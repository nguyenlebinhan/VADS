import logging
from pathlib import PurePath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.exceptions import AppError, ConflictError, NotFoundError
from app.model.base import utcnow
from app.model.documents import Document
from app.model.processing import JobType, ProcessingJob, ProcessingStatus, ProcessingStep
from app.model.repositories.documents import DocumentRepository
from app.model.repositories.processing import ProcessingJobRepository
from app.model.repositories.workspaces import WorkspaceRepository
from app.model.schemas.documents import (
    DocumentDeleteResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.model.schemas.processing import ProcessingStatusResponse
from app.model.storage import DocumentFile, StorageProvider
from app.service.base import Service
from app.service.processing import ProcessingStateService
from app.service.storage import ObjectStorage
from app.utils.file_validator import FileValidator, ValidatedUpload
from app.utils.task_dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)


class DocumentService(Service):
    def __init__(
        self,
        session: Session,
        *,
        storage: ObjectStorage,
        dispatcher: TaskDispatcher,
        settings: Settings,
    ) -> None:
        super().__init__(session)
        self.storage = storage
        self.dispatcher = dispatcher
        self.settings = settings
        self.repository = DocumentRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.processing_repository = ProcessingJobRepository(session)
        self.processing_service = ProcessingStateService(session)
        self.validator = FileValidator(settings)

    def upload(
        self,
        workspace_id: str,
        upload: UploadFile,
        *,
        display_name: str | None = None,
        uploaded_by: str | None = None,
        commune_id: str | None = None,
        owner_id: str | None = None,
    ) -> DocumentUploadResponse:
        workspace = self.workspace_repository.get_active(workspace_id)
        if workspace is None:
            raise NotFoundError("WORKSPACE", workspace_id)

        validated = self.validator.validate(upload)
        try:
            duplicate = self.repository.find_active_duplicate(workspace_id, validated.checksum)
            if duplicate is not None:
                self._raise_duplicate(duplicate)

            document_id = f"doc-{uuid4()}"
            stored_filename = f"{uuid4().hex}{validated.extension}"
            resolved_display_name = self._display_name(display_name, validated)
            object_key = (
                f"workspaces/{workspace_id}/documents/{document_id}/original/{stored_filename}"
            )
            self.storage.upload(
                validated.file_object,
                object_key=object_key,
                content_type=validated.mime_type,
                metadata={
                    "document-id": document_id,
                    "sha256": validated.checksum,
                },
            )

            document = Document(
                id=document_id,
                commune_id=commune_id,
                owner_id=owner_id,
                workspace_id=workspace_id,
                uploaded_by=uploaded_by,
                display_name=resolved_display_name,
                original_filename=validated.original_filename,
                mime_type=validated.mime_type,
                file_extension=validated.extension,
                file_size=validated.file_size,
                checksum=validated.checksum,
                status=ProcessingStatus.UPLOADED,
            )
            document_file = DocumentFile(
                document_id=document_id,
                storage_provider=StorageProvider(self.settings.storage_provider),
                bucket_name=self.storage.bucket_name,
                object_key=object_key,
                original_filename=validated.original_filename,
                stored_filename=stored_filename,
                mime_type=validated.mime_type,
                file_size=validated.file_size,
                checksum=validated.checksum,
            )
            job = ProcessingJob(
                document_id=document_id,
                job_type=JobType.DOCUMENT_PROCESSING,
                status=ProcessingStatus.UPLOADED,
                progress=0,
                current_step=ProcessingStep.VALIDATING_FILE,
                attempt=1,
                message="Tài liệu đang chờ xử lý",
            )
            self.session.add_all([document, document_file, job])
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
                self._delete_uploaded_object(object_key)
                raced_duplicate = self.repository.find_active_duplicate(
                    workspace_id, validated.checksum
                )
                if raced_duplicate is not None:
                    self._raise_duplicate(raced_duplicate)
                raise
            except Exception:
                self.session.rollback()
                self._delete_uploaded_object(object_key)
                raise

            try:
                self.dispatcher.enqueue_processing(job.id)
            except Exception:
                # The durable UPLOADED row is an outbox-like recovery point.
                # Celery Beat redispatches these jobs after the broker recovers.
                logger.exception(
                    "Could not dispatch processing job",
                    extra={"job_id": job.id, "document_id": document_id},
                )

            return DocumentUploadResponse(
                document_id=document_id,
                workspace_id=workspace_id,
                status=ProcessingStatus.UPLOADED,
                progress=0,
                current_step=ProcessingStep.VALIDATING_FILE,
            )
        finally:
            validated.close()

    def get(self, document_id: str) -> DocumentResponse:
        document = self._get_active(document_id)
        job = self.processing_service.get_latest(document_id)
        return DocumentResponse(
            document_id=document.id,
            workspace_id=document.workspace_id,
            display_name=document.display_name,
            original_filename=document.original_filename,
            mime_type=document.mime_type,
            file_extension=document.file_extension,
            file_size=document.file_size,
            checksum=document.checksum,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            total_pages=document.total_pages,
            document_type=document.document_type,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    def get_status(self, document_id: str) -> ProcessingStatusResponse:
        self._get_active(document_id)
        job = self.processing_service.get_latest(document_id)
        return self.processing_service.to_response(job)

    def reprocess(self, document_id: str) -> DocumentUploadResponse:
        document = self.repository.get_active(document_id, for_update=True)
        if document is None:
            raise NotFoundError("DOCUMENT", document_id)
        latest = self.processing_repository.get_latest_for_document(document_id)
        if latest is not None and latest.status in {
            ProcessingStatus.UPLOADED,
            ProcessingStatus.QUEUED,
            ProcessingStatus.PROCESSING,
        }:
            raise ConflictError(
                "DOCUMENT_ALREADY_PROCESSING",
                "Tài liệu đang có một processing job chưa hoàn tất.",
                {"jobId": latest.id},
            )
        attempt = (latest.attempt if latest else 0) + 1
        job = ProcessingJob(
            document_id=document_id,
            job_type=JobType.DOCUMENT_PROCESSING,
            attempt=attempt,
            status=ProcessingStatus.UPLOADED,
            progress=0,
            current_step=ProcessingStep.VALIDATING_FILE,
            message="Tài liệu đang chờ xử lý lại",
        )
        document.status = ProcessingStatus.UPLOADED
        self.session.add(job)
        self.session.commit()
        try:
            self.dispatcher.enqueue_processing(job.id)
        except Exception:
            logger.exception(
                "Could not dispatch reprocessing job",
                extra={"job_id": job.id, "document_id": document_id},
            )
        return DocumentUploadResponse(
            document_id=document_id,
            workspace_id=document.workspace_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
        )

    def soft_delete(self, document_id: str) -> DocumentDeleteResponse:
        document = self.repository.get_active(document_id, for_update=True)
        if document is None:
            raise NotFoundError("DOCUMENT", document_id)

        now = utcnow()
        job = self.processing_repository.get_latest_for_document(document_id)
        if job is not None and job.status not in {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
            ProcessingStatus.NEEDS_REVIEW,
        }:
            self.processing_service.transition(
                job.id,
                status=ProcessingStatus.CANCELLED,
                progress=job.progress,
                current_step=job.current_step,
                error_code="DOCUMENT_DELETED",
                error_message="Tài liệu đã bị xoá trước khi xử lý hoàn tất.",
                commit=False,
            )
        document.deleted_at = now
        document.is_deleted = True
        document.updated_at = now
        self.session.commit()

        if self.settings.delete_object_on_soft_delete:
            try:
                self.dispatcher.enqueue_purge(document_id)
            except Exception:
                logger.exception(
                    "Could not dispatch object purge",
                    extra={"document_id": document_id},
                )
        return DocumentDeleteResponse(document_id=document_id)

    def _get_active(self, document_id: str) -> Document:
        document = self.repository.get_active(document_id)
        if document is None:
            raise NotFoundError("DOCUMENT", document_id)
        return document

    @staticmethod
    def _display_name(display_name: str | None, validated: ValidatedUpload) -> str:
        if display_name is None:
            return PurePath(validated.original_filename).stem
        normalized = display_name.strip()
        if not normalized:
            raise AppError(
                status_code=422,
                code="INVALID_DISPLAY_NAME",
                message="Tên hiển thị không được để trống.",
            )
        if len(normalized) > 255:
            raise AppError(
                status_code=422,
                code="INVALID_DISPLAY_NAME",
                message="Tên hiển thị không được dài quá 255 ký tự.",
            )
        return normalized

    @staticmethod
    def _raise_duplicate(duplicate: Document) -> None:
        raise ConflictError(
            "DUPLICATE_DOCUMENT",
            "Tệp này đã tồn tại trong workspace.",
            {"existingDocumentId": duplicate.id, "checksum": duplicate.checksum},
        )

    def _delete_uploaded_object(self, object_key: str) -> None:
        try:
            self.storage.delete(object_key=object_key)
        except Exception:
            logger.exception(
                "Compensating object deletion failed",
                extra={"object_key": object_key},
            )

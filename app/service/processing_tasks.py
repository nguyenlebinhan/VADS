import logging

from sqlalchemy import select

from app.config.celery_app import celery_app
from app.config.database import SessionLocal
from app.config.settings import get_settings
from app.exceptions import (
    AppError,
    InvalidStateTransitionError,
    NotFoundError,
    StorageUnavailableError,
)
from app.extraction.dependencies import build_ocr_provider
from app.model.base import utcnow
from app.model.documents import Document
from app.model.extraction import DocumentPage
from app.model.processing import ProcessingStatus, ProcessingStep
from app.model.repositories.processing import ProcessingJobRepository
from app.model.repositories.storage import DocumentFileRepository
from app.processing.pipeline import DocumentProcessingPipeline
from app.service.processing import ProcessingStateService
from app.utils.storage_dependencies import get_object_storage

logger = logging.getLogger(__name__)


@celery_app.task(name="vads.processing.mark_queued")
def mark_queued(job_id: str) -> None:
    """Idempotently claim a durable UPLOADED job."""

    with SessionLocal() as session:
        job = ProcessingJobRepository(session).get(job_id)
        if job is None or job.status != ProcessingStatus.UPLOADED:
            return
        try:
            ProcessingStateService(session).transition(
                job_id,
                status=ProcessingStatus.QUEUED,
                progress=0,
                current_step=ProcessingStep.VALIDATING_FILE,
                message="Tài liệu đang chờ xử lý",
            )
        except (InvalidStateTransitionError, NotFoundError):
            session.rollback()


@celery_app.task(name="vads.processing.process_document")
def process_document(job_id: str) -> None:
    settings = get_settings()
    storage = get_object_storage()
    with SessionLocal() as session:
        repository = ProcessingJobRepository(session)
        job = repository.get(job_id)
        if job is None or job.status in {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
            ProcessingStatus.NEEDS_REVIEW,
        }:
            return
        try:
            if job.status == ProcessingStatus.UPLOADED:
                ProcessingStateService(session).transition(
                    job_id,
                    status=ProcessingStatus.QUEUED,
                    progress=0,
                    current_step=ProcessingStep.VALIDATING_FILE,
                    message="Tài liệu đang chờ xử lý",
                )
            DocumentProcessingPipeline(
                session,
                storage=storage,
                ocr_provider=build_ocr_provider(settings),
                settings=settings,
            ).run(job_id)
        except Exception as exc:
            session.rollback()
            logger.exception("Document processing failed", extra={"job_id": job_id})
            failed_job = repository.get(job_id)
            if failed_job is None or failed_job.status in {
                ProcessingStatus.COMPLETED,
                ProcessingStatus.CANCELLED,
                ProcessingStatus.NEEDS_REVIEW,
            }:
                return
            error_code = exc.code if isinstance(exc, AppError) else "DOCUMENT_PROCESSING_FAILED"
            error_message = (
                exc.message if isinstance(exc, AppError) else "Không thể xử lý tài liệu."
            )
            ProcessingStateService(session).transition(
                job_id,
                status=ProcessingStatus.FAILED,
                progress=failed_job.progress,
                current_step=failed_job.current_step,
                current_page=failed_job.current_page,
                total_pages=failed_job.total_pages,
                message=error_message,
                error_code=error_code,
                error_message=error_message,
            )


@celery_app.task(name="vads.processing.redispatch_uploaded_jobs")
def redispatch_uploaded_jobs() -> int:
    """Recover jobs committed while Redis/Celery was unavailable."""

    with SessionLocal() as session:
        jobs = ProcessingJobRepository(session).list_uploaded(limit=100)
        for job in jobs:
            process_document.apply_async(args=[job.id])
        return len(jobs)


@celery_app.task(
    name="vads.processing.purge_document_objects",
    autoretry_for=(StorageUnavailableError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=8,
)
def purge_document_objects(document_id: str) -> int:
    storage = get_object_storage()
    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if document is None or document.deleted_at is None:
            return 0
        files = DocumentFileRepository(session).list_for_document(document_id)
        deleted_count = 0
        for document_file in files:
            storage.delete(object_key=document_file.object_key)
            document_file.deleted_at = utcnow()
            deleted_count += 1
        page_keys = session.scalars(
            select(DocumentPage.rendered_object_key).where(
                DocumentPage.document_id == document_id,
                DocumentPage.rendered_object_key.is_not(None),
            )
        )
        for object_key in page_keys:
            if object_key:
                storage.delete(object_key=object_key)
                deleted_count += 1
        session.commit()
        return deleted_count

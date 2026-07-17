from sqlalchemy.orm import Session

from app.exceptions import AppError, InvalidStateTransitionError, NotFoundError
from app.model.base import utcnow
from app.model.processing import ProcessingJob, ProcessingStatus, ProcessingStep
from app.model.repositories.processing import ProcessingJobRepository
from app.model.schemas.processing import ProcessingStatusResponse
from app.service.base import Service

STEP_MESSAGES: dict[ProcessingStep, str] = {
    ProcessingStep.VALIDATING_FILE: "Đang kiểm tra tệp",
    ProcessingStep.DETECTING_PDF_TYPE: "Đang phân loại tài liệu",
    ProcessingStep.RENDERING_PAGES: "Đang render trang",
    ProcessingStep.OCR_PROCESSING: "Đang nhận dạng và trích xuất văn bản",
    ProcessingStep.DETECTING_STRUCTURE: "Đang nhận diện cấu trúc pháp lý",
    ProcessingStep.CREATING_CHUNKS: "Đang tạo các đoạn dữ liệu có cấu trúc",
    ProcessingStep.GENERATING_SUMMARY: "Đang chờ module tóm tắt",
    ProcessingStep.BUILDING_KNOWLEDGE_GRAPH: "Đang chờ module đồ thị tri thức",
    ProcessingStep.INDEXING_VECTOR_DATA: "Đang chờ module lập chỉ mục",
    ProcessingStep.COMPLETED: "Đã xử lý tài liệu thành công",
}

ALLOWED_TRANSITIONS: dict[ProcessingStatus, set[ProcessingStatus]] = {
    ProcessingStatus.UPLOADED: {
        ProcessingStatus.QUEUED,
        ProcessingStatus.FAILED,
        ProcessingStatus.CANCELLED,
    },
    ProcessingStatus.QUEUED: {
        ProcessingStatus.PROCESSING,
        ProcessingStatus.FAILED,
        ProcessingStatus.CANCELLED,
    },
    ProcessingStatus.PROCESSING: {
        ProcessingStatus.COMPLETED,
        ProcessingStatus.FAILED,
        ProcessingStatus.CANCELLED,
        ProcessingStatus.NEEDS_REVIEW,
    },
    ProcessingStatus.COMPLETED: set(),
    ProcessingStatus.FAILED: set(),
    ProcessingStatus.CANCELLED: set(),
    ProcessingStatus.NEEDS_REVIEW: set(),
}
TERMINAL_STATUSES = {
    ProcessingStatus.COMPLETED,
    ProcessingStatus.FAILED,
    ProcessingStatus.CANCELLED,
    ProcessingStatus.NEEDS_REVIEW,
}


class ProcessingStateService(Service):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.repository = ProcessingJobRepository(session)

    def get_latest(self, document_id: str) -> ProcessingJob:
        job = self.repository.get_latest_for_document(document_id)
        if job is None:
            raise NotFoundError("PROCESSING_JOB", document_id)
        return job

    def transition(
        self,
        job_id: str,
        *,
        status: ProcessingStatus,
        progress: int,
        current_step: ProcessingStep,
        current_page: int | None = None,
        total_pages: int | None = None,
        message: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        commit: bool = True,
    ) -> ProcessingJob:
        job = self.repository.get_for_update(job_id)
        if job is None:
            raise NotFoundError("PROCESSING_JOB", job_id)

        if job.status in TERMINAL_STATUSES:
            if (
                status == job.status
                and progress == job.progress
                and current_step == job.current_step
            ):
                if commit:
                    self.session.commit()
                return job
            raise InvalidStateTransitionError(job.status.value, status.value)
        if status != job.status and status not in ALLOWED_TRANSITIONS[job.status]:
            raise InvalidStateTransitionError(job.status.value, status.value)
        if not 0 <= progress <= 100:
            raise AppError(
                status_code=422,
                code="INVALID_PROCESSING_PROGRESS",
                message="Tiến độ xử lý phải nằm trong khoảng từ 0 đến 100.",
            )
        if progress < job.progress:
            raise AppError(
                status_code=409,
                code="PROCESSING_PROGRESS_REGRESSION",
                message="Tiến độ xử lý không được giảm.",
                details={"currentProgress": job.progress, "targetProgress": progress},
            )
        if current_page is not None and current_page < 0:
            raise AppError(
                status_code=422,
                code="INVALID_CURRENT_PAGE",
                message="Chỉ số trang hiện tại không hợp lệ.",
            )
        if total_pages is not None and total_pages < 0:
            raise AppError(
                status_code=422,
                code="INVALID_TOTAL_PAGES",
                message="Tổng số trang không hợp lệ.",
            )
        if current_page is not None and total_pages is not None and current_page > total_pages:
            raise AppError(
                status_code=422,
                code="INVALID_PAGE_PROGRESS",
                message="Trang hiện tại không được vượt quá tổng số trang.",
            )
        if status == ProcessingStatus.COMPLETED:
            progress = 100
            current_step = ProcessingStep.COMPLETED
        if status == ProcessingStatus.FAILED and not error_message:
            raise AppError(
                status_code=422,
                code="PROCESSING_ERROR_MESSAGE_REQUIRED",
                message="Trạng thái FAILED phải có thông báo lỗi.",
            )

        now = utcnow()
        job.status = status
        job.progress = progress
        job.current_step = current_step
        job.current_page = current_page
        if total_pages is not None:
            job.total_pages = total_pages
        job.message = message
        job.error_code = error_code
        job.error_message = error_message
        job.updated_at = now
        if status == ProcessingStatus.PROCESSING and job.started_at is None:
            job.started_at = now
        if status in TERMINAL_STATUSES:
            job.completed_at = now

        from app.model.documents import Document

        document = self.session.get(Document, job.document_id)
        if document is not None:
            document.status = status
            document.updated_at = now

        if commit:
            self.session.commit()
            self.session.refresh(job)
        else:
            self.session.flush()
        return job

    @staticmethod
    def to_response(job: ProcessingJob) -> ProcessingStatusResponse:
        message = job.message or job.error_message or STEP_MESSAGES[job.current_step]
        return ProcessingStatusResponse(
            document_id=job.document_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            current_page=job.current_page,
            total_pages=job.total_pages,
            message=message,
            started_at=job.started_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            error_code=job.error_code,
            error_message=job.error_message,
        )

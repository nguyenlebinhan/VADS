from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.processing import JobType, ProcessingJob, ProcessingStatus
from app.model.repositories.base import Repository


class ProcessingJobRepository(Repository[ProcessingJob]):
    model = ProcessingJob

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_for_update(self, job_id: str) -> ProcessingJob | None:
        statement = select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
        return self.session.scalar(statement)

    def get_latest_for_document(
        self,
        document_id: str,
        *,
        for_update: bool = False,
    ) -> ProcessingJob | None:
        statement = (
            select(ProcessingJob)
            .where(
                ProcessingJob.document_id == document_id,
                ProcessingJob.job_type == JobType.DOCUMENT_PROCESSING,
            )
            .order_by(ProcessingJob.attempt.desc(), ProcessingJob.created_at.desc())
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_uploaded(self, *, limit: int = 100) -> list[ProcessingJob]:
        statement = (
            select(ProcessingJob)
            .where(ProcessingJob.status == ProcessingStatus.UPLOADED)
            .order_by(ProcessingJob.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

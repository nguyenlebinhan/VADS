from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin, prefixed_uuid

if TYPE_CHECKING:
    from app.model.documents import Document


class ProcessingStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ProcessingStep(str, Enum):
    VALIDATING_FILE = "VALIDATING_FILE"
    DETECTING_PDF_TYPE = "DETECTING_PDF_TYPE"
    RENDERING_PAGES = "RENDERING_PAGES"
    OCR_PROCESSING = "OCR_PROCESSING"
    DETECTING_STRUCTURE = "DETECTING_STRUCTURE"
    CREATING_CHUNKS = "CREATING_CHUNKS"
    GENERATING_SUMMARY = "GENERATING_SUMMARY"
    BUILDING_KNOWLEDGE_GRAPH = "BUILDING_KNOWLEDGE_GRAPH"
    INDEXING_VECTOR_DATA = "INDEXING_VECTOR_DATA"
    COMPLETED = "COMPLETED"


class JobType(str, Enum):
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"


class ProcessingJob(TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),
        UniqueConstraint(
            "document_id",
            "job_type",
            "attempt",
            name="uq_processing_job_document_type_attempt",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("job"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[JobType] = mapped_column(
        SAEnum(
            JobType,
            name="job_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=JobType.DOCUMENT_PROCESSING,
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(
            ProcessingStatus,
            name="processing_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ProcessingStatus.UPLOADED,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_step: Mapped[ProcessingStep] = mapped_column(
        SAEnum(
            ProcessingStep,
            name="processing_step",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ProcessingStep.VALIDATING_FILE,
    )
    current_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="processing_jobs")

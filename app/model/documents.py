from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin, prefixed_uuid
from app.model.processing import ProcessingStatus

if TYPE_CHECKING:
    from app.model.chunking import DocumentChunk
    from app.model.extraction import DocumentPage, DocumentTable
    from app.model.processing import ProcessingJob
    from app.model.storage import DocumentFile
    from app.model.structure import DocumentSection
    from app.model.users import User
    from app.model.workspaces import Workspace


class DocumentType(str, Enum):
    TEXT_BASED = "TEXT_BASED"
    SCANNED = "SCANNED"
    HYBRID = "HYBRID"
    DOCX = "DOCX"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "uq_documents_workspace_checksum_active",
            "workspace_id",
            "checksum",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("doc"))
    workspace_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(
            ProcessingStatus,
            name="document_processing_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ProcessingStatus.UPLOADED,
        index=True,
    )
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_type: Mapped[DocumentType | None] = mapped_column(
        SAEnum(
            DocumentType,
            name="document_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="documents")
    uploader: Mapped["User | None"] = relationship("User", back_populates="documents")
    files: Mapped[list["DocumentFile"]] = relationship("DocumentFile", back_populates="document")
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ProcessingJob.attempt",
    )
    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    sections: Mapped[list["DocumentSection"]] = relationship(
        "DocumentSection", back_populates="document", cascade="all, delete-orphan"
    )
    tables: Mapped[list["DocumentTable"]] = relationship(
        "DocumentTable", back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

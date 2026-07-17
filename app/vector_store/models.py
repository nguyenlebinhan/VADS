from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin

EMBEDDING_DIMENSION = 384


class IndexStatus(str, Enum):
    QUEUED = "QUEUED"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EmbeddingRecord(TimestampMixin, Base):
    __tablename__ = "document_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "embedding_model",
            "embedding_version",
            name="uq_embedding_chunk_model_version",
        ),
        Index("ix_embeddings_workspace_document", "workspace_id", "document_id"),
        Index("ix_embeddings_legal_path", "document_id", "chapter", "article", "clause"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    chunk_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    vector: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    chapter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    article: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    point: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    printed_page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    printed_page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entity_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    node_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    agency: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False)


class DocumentIndexJob(TimestampMixin, Base):
    __tablename__ = "document_index_jobs"
    __table_args__ = (
        UniqueConstraint("document_id", "attempt", name="uq_index_job_document_attempt"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[IndexStatus] = mapped_column(
        SAEnum(
            IndexStatus,
            name="document_index_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=IndexStatus.QUEUED,
        index=True,
    )
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    embedding_models: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

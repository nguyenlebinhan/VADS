from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class Citation(TimestampMixin, Base):
    __tablename__ = "citations"
    __table_args__ = (
        Index("ix_citations_owner", "owner_type", "owner_id"),
        Index("ix_citations_document_chunk", "document_id", "chunk_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("cite"))
    owner_type: Mapped[str] = mapped_column(String(40), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(40), nullable=False)
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_quote: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    bounding_box: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    article: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    point: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_confidence: Mapped[float] = mapped_column(Float, nullable=False)

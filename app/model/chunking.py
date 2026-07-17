from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin, prefixed_uuid

if TYPE_CHECKING:
    from app.model.documents import Document
    from app.model.structure import DocumentSection


class DocumentChunk(TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_order", "document_id", "order_index"),
        Index("ix_document_chunks_section", "section_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("chunk"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    chapter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    article: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    point: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appendix: Mapped[str | None] = mapped_column(String(255), nullable=True)
    form_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    printed_page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    printed_page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_block_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("page_blocks.id", ondelete="RESTRICT"), nullable=False
    )
    end_block_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("page_blocks.id", ondelete="RESTRICT"), nullable=False
    )
    bounding_boxes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
    section_ref: Mapped[DocumentSection | None] = relationship("DocumentSection")

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin, prefixed_uuid

if TYPE_CHECKING:
    from app.model.documents import Document
    from app.model.structure import DocumentSection


class DocumentPage(TimestampMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_index", name="uq_document_page_index"),
        Index("ix_document_pages_document_order", "document_id", "page_index"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("page"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    printed_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_text_layer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_ocr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rendered_object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    document: Mapped[Document] = relationship("Document", back_populates="pages")
    blocks: Mapped[list[PageBlock]] = relationship(
        "PageBlock",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="PageBlock.order_index",
    )


class PageBlock(TimestampMixin, Base):
    __tablename__ = "page_blocks"
    __table_args__ = (
        UniqueConstraint("page_id", "order_index", name="uq_page_block_order"),
        Index(
            "ix_page_blocks_document_page_order",
            "document_id",
            "page_id",
            "order_index",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("block"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(String(50), nullable=False, default="PARAGRAPH")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="TEXT_LAYER")

    page: Mapped[DocumentPage] = relationship("DocumentPage", back_populates="blocks")


class DocumentTable(TimestampMixin, Base):
    __tablename__ = "document_tables"
    __table_args__ = (
        Index(
            "ix_document_tables_document_order",
            "document_id",
            "page_start",
            "order_index",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("table"))
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
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_block_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("page_blocks.id", ondelete="SET NULL"), nullable=True
    )
    end_block_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("page_blocks.id", ondelete="SET NULL"), nullable=True
    )
    bounding_boxes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    header_rows: Mapped[list[list[str]]] = mapped_column(JSON, nullable=False, default=list)
    rows: Mapped[list[list[str]]] = mapped_column(JSON, nullable=False, default=list)

    document: Mapped[Document] = relationship("Document", back_populates="tables")
    section: Mapped[DocumentSection | None] = relationship("DocumentSection")

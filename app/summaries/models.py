from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class DocumentSummary(TimestampMixin, Base):
    __tablename__ = "document_summaries"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_summary_version"),
        Index("ix_document_summaries_current", "document_id", "is_current"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("sum"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflows.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rejected_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SummaryItem(TimestampMixin, Base):
    __tablename__ = "summary_items"
    __table_args__ = (Index("ix_summary_items_summary_order", "summary_id", "order_index"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("sitem"))
    summary_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("document_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    system_metadata: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

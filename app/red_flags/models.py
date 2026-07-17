from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class RedFlag(TimestampMixin, Base):
    __tablename__ = "red_flags"
    __table_args__ = (
        Index("ix_red_flags_document_severity", "document_id", "severity"),
        Index("ix_red_flags_document_status", "document_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("flag"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    graph_version_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("graph_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_edge_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    verification_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RedFlagNode(Base):
    __tablename__ = "red_flag_nodes"

    red_flag_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("red_flags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    node_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )


class CriticalQuestion(TimestampMixin, Base):
    __tablename__ = "critical_questions"
    __table_args__ = (Index("ix_critical_questions_document_created", "document_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("question"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    red_flag_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("red_flags.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    related_subject: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_location: Mapped[str] = mapped_column(String(1000), nullable=False)
    risk_if_unresolved: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
    verification_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

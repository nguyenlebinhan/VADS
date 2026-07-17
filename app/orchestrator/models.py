from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class AIWorkflow(TimestampMixin, Base):
    __tablename__ = "ai_workflows"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("wf"))
    document_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    intent: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    private_processing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIWorkflowStep(TimestampMixin, Base):
    __tablename__ = "ai_workflow_steps"
    __table_args__ = (
        Index(
            "uq_ai_workflow_steps_workflow_key",
            "workflow_id",
            "step_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("wfstep"))
    workflow_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    executor: Mapped[str] = mapped_column(String(100), nullable=False)
    reason_for_selection: Mapped[str] = mapped_column(Text, nullable=False)
    depends_on: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    can_run_in_parallel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_output_schema: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    output: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

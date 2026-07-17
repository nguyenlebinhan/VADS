from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, prefixed_uuid


class ModelExecution(Base):
    __tablename__ = "model_executions"
    __table_args__ = (
        Index("ix_model_executions_workflow_step", "workflow_id", "workflow_step_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("mexec"))
    workflow_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_step_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflow_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_alias: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_snapshot: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

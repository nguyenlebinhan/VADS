from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class RegulatoryDocumentStatus(str, Enum):
    PARSED = "PARSED"
    ANALYZED = "ANALYZED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class ChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"
    MOVED = "MOVED"
    RENUMBERED = "RENUMBERED"
    CLARIFIED = "CLARIFIED"
    VALUE_CHANGED = "VALUE_CHANGED"
    DEADLINE_CHANGED = "DEADLINE_CHANGED"
    RESPONSIBILITY_CHANGED = "RESPONSIBILITY_CHANGED"
    SCOPE_CHANGED = "SCOPE_CHANGED"
    PROCEDURE_CHANGED = "PROCEDURE_CHANGED"
    LEGAL_BASIS_CHANGED = "LEGAL_BASIS_CHANGED"


class ImpactLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_RETRY = "NEEDS_RETRY"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class RegulatoryDocumentFamily(TimestampMixin, Base):
    __tablename__ = "regulatory_document_families"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("rdf"))
    workspace_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_key: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("workspace_id", "family_key", name="uq_reg_family_workspace_key"),
    )


class RegulatoryDocumentVersion(TimestampMixin, Base):
    __tablename__ = "regulatory_document_versions"
    __table_args__ = (
        UniqueConstraint("family_id", "version_number", name="uq_reg_family_version"),
        UniqueConstraint("document_id", name="uq_reg_version_document"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("rdv"))
    family_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("regulatory_document_families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_number: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    legal_document_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    issuing_agency: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    issued_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    applicable_subjects: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RegulatoryDocumentStatus] = mapped_column(
        SAEnum(
            RegulatoryDocumentStatus,
            name="regulatory_document_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=RegulatoryDocumentStatus.PARSED,
        index=True,
    )


class RegulatorySection(TimestampMixin, Base):
    __tablename__ = "regulatory_sections"
    __table_args__ = (
        UniqueConstraint("document_version_id", "order_index", name="uq_reg_section_order"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("rds"))
    document_version_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("regulatory_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    legal_location: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RegulatoryChange(TimestampMixin, Base):
    __tablename__ = "regulatory_changes"
    __table_args__ = (
        UniqueConstraint("new_version_id", "fact_key", name="uq_reg_change_version_fact"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("rch"))
    old_version_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("regulatory_document_versions.id"), nullable=False, index=True
    )
    new_version_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("regulatory_document_versions.id"), nullable=False, index=True
    )
    change_type: Mapped[ChangeType] = mapped_column(
        SAEnum(
            ChangeType,
            name="regulatory_change_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    new_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class RegulatoryProject(TimestampMixin, Base):
    __tablename__ = "regulatory_projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "project_code", name="uq_reg_project_workspace_code"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("prj"))
    workspace_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    locations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    lead_department: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    coordinating_departments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    legal_bases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    activities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    budget_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    timeline: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class RegulatoryAgentRun(TimestampMixin, Base):
    __tablename__ = "regulatory_agent_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("run"))
    document_version_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("regulatory_document_versions.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(
            AgentRunStatus,
            name="regulatory_agent_run_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=AgentRunStatus.PENDING,
        index=True,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RegulatoryAgentTask(TimestampMixin, Base):
    __tablename__ = "regulatory_agent_tasks"
    __table_args__ = (
        UniqueConstraint("agent_run_id", "sequence_number", name="uq_reg_task_sequence"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("task"))
    agent_run_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("regulatory_agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(
            AgentRunStatus,
            name="regulatory_agent_task_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    input_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RegulatoryAgentOutput(TimestampMixin, Base):
    __tablename__ = "regulatory_agent_outputs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("out"))
    agent_task_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("regulatory_agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class RegulatoryImpact(TimestampMixin, Base):
    __tablename__ = "regulatory_impacts"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "project_id",
            "agent_run_id",
            name="uq_reg_impact_version_project_run",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("imp"))
    document_version_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("regulatory_document_versions.id"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("regulatory_projects.id"), nullable=False, index=True
    )
    agent_run_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("regulatory_agent_runs.id"), nullable=False, index=True
    )
    impact_level: Mapped[ImpactLevel] = mapped_column(
        SAEnum(
            ImpactLevel,
            name="regulatory_impact_level",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_areas: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    departments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    recommended_actions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(String(60), nullable=False, default="PENDING")
    reviewed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RegulatoryVerificationResult(TimestampMixin, Base):
    __tablename__ = "regulatory_verification_results"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("vrf"))
    agent_run_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("regulatory_agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(
            AgentRunStatus,
            name="regulatory_verification_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    checked_claims: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_claims: Mapped[int] = mapped_column(Integer, nullable=False)

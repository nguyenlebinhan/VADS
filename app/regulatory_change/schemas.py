from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from app.common.contracts import APIModel
from app.regulatory_change.models import AgentRunStatus, ChangeType, ImpactLevel


class RegulatoryDocumentData(APIModel):
    id: str
    document_id: str
    family_id: str
    family_key: str
    version_number: int
    title: str
    document_number: str
    document_type: str
    issuing_agency: str
    issued_date: date
    effective_date: date
    domain: str
    applicable_subjects: list[str]
    status: str
    executive_summary: str
    created_at: datetime


class RegulatoryUploadData(RegulatoryDocumentData):
    processing_status: str


class RegulatorySectionData(APIModel):
    id: str
    section_type: str
    label: str | None = None
    title: str | None = None
    legal_location: str
    content: str
    order_index: int
    page_start: int | None = None
    page_end: int | None = None


class ChangeData(APIModel):
    id: str
    change_type: ChangeType
    status: str | None = None
    fact_key: str
    old_value: str | None = None
    new_value: str | None = None
    effective_year: int | None = None
    old_location: str | None = None
    new_location: str | None = None
    summary: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[dict[str, Any]]


class TimelineEntry(APIModel):
    document_id: str
    version_number: int
    issued_date: date
    effective_date: date
    values: dict[str, str]


class ProjectCreate(APIModel):
    workspace_id: str = Field(min_length=1, max_length=40)
    project_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=500)
    status: str = Field(min_length=1, max_length=60)
    domain: str = Field(min_length=1, max_length=160)
    locations: list[str] = Field(default_factory=list)
    lead_department: str = Field(min_length=1, max_length=300)
    coordinating_departments: list[str] = Field(default_factory=list)
    legal_bases: list[str] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    budget_sources: list[str] = Field(default_factory=list)
    timeline: dict[str, Any] = Field(default_factory=dict)
    sections: list[dict[str, Any]] = Field(default_factory=list)


class ProjectData(ProjectCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class ImpactData(APIModel):
    id: str
    document_version_id: str
    document_id: str
    project_id: str
    project_name: str
    agent_run_id: str
    impact_level: ImpactLevel
    confidence: float = Field(ge=0, le=1)
    reason: str
    affected_areas: list[dict[str, Any]]
    departments: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    review_status: str
    reviewed_by: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ImpactReviewRequest(APIModel):
    status: str = Field(pattern="^(ACCEPTED|REJECTED|NEEDS_HUMAN_REVIEW)$")
    reviewed_by: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=2000)


class AgentTaskData(APIModel):
    id: str
    agent_name: str
    sequence_number: int
    status: AgentRunStatus
    input_references: list[dict[str, Any]]
    result: dict[str, Any] | None = None
    confidence: float | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class VerificationData(APIModel):
    status: AgentRunStatus
    confidence: float = Field(ge=0, le=1)
    issues: list[str]
    checked_claims: int
    rejected_claims: int


class AgentRunData(APIModel):
    id: str
    document_version_id: str
    document_id: str
    status: AgentRunStatus
    attempt: int
    tasks: list[AgentTaskData]
    verification: VerificationData | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


class AnalyzeData(APIModel):
    run: AgentRunData
    changes: list[ChangeData]
    impacts: list[ImpactData]


class AnalyzeRequest(APIModel):
    force: bool = False


class RegulatoryUploadMetadata(APIModel):
    workspace_id: str = Field(min_length=1, max_length=40)
    family_key: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    document_number: str = Field(min_length=1, max_length=160)
    document_type: str = Field(min_length=1, max_length=80)
    issuing_agency: str = Field(min_length=1, max_length=300)
    issued_date: date
    effective_date: date
    domain: str = Field(min_length=1, max_length=160)
    applicable_subjects: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def effective_date_not_before_issue(self):
        if self.effective_date < self.issued_date:
            raise ValueError("effectiveDate must be on or after issuedDate")
        return self

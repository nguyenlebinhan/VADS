from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import Field

from app.citations.schemas import CitationDraft, CitationView
from app.common.contracts import APIModel


class RedFlagRule(str, Enum):
    MISSING_RESPONSIBLE_ACTOR = "MISSING_RESPONSIBLE_ACTOR"
    MISSING_LEAD_AGENCY = "MISSING_LEAD_AGENCY"
    MISSING_FUNDING_SOURCE = "MISSING_FUNDING_SOURCE"
    MISSING_BUDGET_AMOUNT = "MISSING_BUDGET_AMOUNT"
    MISSING_DEADLINE = "MISSING_DEADLINE"
    DEADLINE_WITHOUT_OUTPUT = "DEADLINE_WITHOUT_OUTPUT"
    MULTIPLE_LEAD_AGENCIES = "MULTIPLE_LEAD_AGENCIES"
    CONFLICTING_RESPONSIBILITY = "CONFLICTING_RESPONSIBILITY"
    CONFLICTING_BUDGET = "CONFLICTING_BUDGET"
    CONFLICTING_DEADLINE = "CONFLICTING_DEADLINE"
    BROKEN_LEGAL_REFERENCE = "BROKEN_LEGAL_REFERENCE"
    MISSING_REFERENCED_FORM = "MISSING_REFERENCED_FORM"
    DOSSIER_WITHOUT_RECEIVING_AUTHORITY = "DOSSIER_WITHOUT_RECEIVING_AUTHORITY"
    LOW_CONFIDENCE_CRITICAL_TEXT = "LOW_CONFIDENCE_CRITICAL_TEXT"


class RedFlagSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RedFlagStatus(str, Enum):
    DETECTED = "DETECTED"
    VERIFIED = "VERIFIED"
    SUPPRESSED = "SUPPRESSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class QuestionVerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class RedFlagDraft(APIModel):
    flag_id: str = Field(default_factory=lambda: str(uuid4()))
    issue_type: RedFlagRule
    severity: RedFlagSeverity
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    related_node_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)
    citations: list[CitationDraft] = Field(default_factory=list)
    evidence: dict[str, object] = Field(default_factory=dict)
    status: RedFlagStatus = RedFlagStatus.DETECTED
    verification_model: str | None = None
    verification_reason: str | None = None


class RedFlagOutput(APIModel):
    flags: list[RedFlagDraft] = Field(default_factory=list)


class RedFlagVerificationDecision(APIModel):
    flag_id: str
    verified: bool
    evidence_sufficient: bool
    reason: str


class RedFlagVerificationOutput(APIModel):
    decisions: list[RedFlagVerificationDecision] = Field(default_factory=list)


class RedFlagView(APIModel):
    id: str
    document_id: str
    graph_version_id: str
    issue_type: RedFlagRule
    severity: RedFlagSeverity
    title: str
    description: str
    related_node_ids: list[str]
    related_edge_ids: list[str]
    evidence: dict[str, object]
    status: RedFlagStatus
    verification_model: str | None = None
    verification_reason: str | None = None
    citations: list[CitationView] = Field(default_factory=list)
    created_at: datetime


class CriticalQuestionDraft(APIModel):
    question: str = Field(min_length=15)
    reason: str = Field(min_length=10)
    issue_type: RedFlagRule
    severity: RedFlagSeverity
    related_subject: str = Field(min_length=2)
    source_location: str = Field(min_length=2)
    risk_if_unresolved: str = Field(min_length=5)
    citations: list[CitationDraft] = Field(min_length=1)


class CriticalQuestionOutput(APIModel):
    questions: list[CriticalQuestionDraft] = Field(default_factory=list, max_length=5)


class QuestionVerificationDecision(APIModel):
    question_index: int = Field(ge=0, le=4)
    verified: bool
    evidence_sufficient: bool
    reason: str


class QuestionVerificationOutput(APIModel):
    decisions: list[QuestionVerificationDecision] = Field(default_factory=list)


class VerifiedCriticalQuestion(APIModel):
    draft: CriticalQuestionDraft
    verification_status: QuestionVerificationStatus
    verification_model: str | None = None


class VerifiedCriticalQuestionOutput(APIModel):
    questions: list[VerifiedCriticalQuestion] = Field(default_factory=list, max_length=5)


class CriticalQuestionView(APIModel):
    id: str
    document_id: str
    workflow_id: str
    question: str
    reason: str
    issue_type: RedFlagRule
    severity: RedFlagSeverity
    related_subject: str
    source_location: str
    risk_if_unresolved: str
    citations: list[CitationView]
    verification_status: QuestionVerificationStatus
    verification_model: str | None = None
    created_at: datetime


class CriticalQuestionGenerationResult(APIModel):
    workflow_id: str
    questions: list[CriticalQuestionView] = Field(default_factory=list)

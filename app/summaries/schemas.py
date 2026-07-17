from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, model_validator

from app.citations.schemas import CitationDraft, CitationView
from app.common.contracts import APIModel


class SummaryCategory(str, Enum):
    DOCUMENT_INFORMATION = "DOCUMENT_INFORMATION"
    ENACTMENT_CONTEXT = "ENACTMENT_CONTEXT"
    OBJECTIVE = "OBJECTIVE"
    SCOPE = "SCOPE"
    APPLICABLE_SUBJECT = "APPLICABLE_SUBJECT"
    PRINCIPLE = "PRINCIPLE"
    RESPONSIBILITY = "RESPONSIBILITY"
    AUTHORITY = "AUTHORITY"
    DOSSIER = "DOSSIER"
    PROCEDURE = "PROCEDURE"
    DEADLINE = "DEADLINE"
    RESOURCE = "RESOURCE"
    TRANSITIONAL_PROVISION = "TRANSITIONAL_PROVISION"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"
    APPENDIX_FORM = "APPENDIX_FORM"
    DECISION_POINT = "DECISION_POINT"


class SummaryImportance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SummaryStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUPERSEDED = "SUPERSEDED"
    FAILED = "FAILED"


class SummaryItemStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SummaryItemDraft(APIModel):
    category: SummaryCategory
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    importance: SummaryImportance
    confidence: float = Field(ge=0, le=1)
    citations: list[CitationDraft] = Field(default_factory=list)
    system_metadata: bool = False

    @model_validator(mode="after")
    def metadata_exception_is_narrow(self) -> SummaryItemDraft:
        if self.system_metadata and self.category != SummaryCategory.DOCUMENT_INFORMATION:
            raise ValueError("Only DOCUMENT_INFORMATION can be marked as system metadata")
        return self


class RejectedSummaryItem(APIModel):
    title: str
    reason: str


class DocumentSummaryOutput(APIModel):
    items: list[SummaryItemDraft] = Field(default_factory=list)
    rejected_items: list[RejectedSummaryItem] = Field(default_factory=list)


class SummaryItemRepairOutput(APIModel):
    item: SummaryItemDraft


class SummaryItemView(APIModel):
    id: str
    category: SummaryCategory
    title: str
    content: str
    importance: SummaryImportance
    confidence: float
    status: SummaryItemStatus
    order_index: int
    system_metadata: bool
    citations: list[CitationView] = Field(default_factory=list)


class DocumentSummaryView(APIModel):
    id: str
    document_id: str
    workflow_id: str
    version: int
    model_name: str
    prompt_version: str
    status: SummaryStatus
    is_current: bool
    created_at: datetime
    updated_at: datetime
    items: list[SummaryItemView] = Field(default_factory=list)


class SummaryGenerationResult(APIModel):
    workflow_id: str
    summary: DocumentSummaryView | None = None

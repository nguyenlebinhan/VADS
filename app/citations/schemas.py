from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, model_validator

from app.common.contracts import APIModel, BoundingBox


class CitationOwnerType(str, Enum):
    SUMMARY_ITEM = "SUMMARY_ITEM"
    KNOWLEDGE_NODE = "KNOWLEDGE_NODE"
    KNOWLEDGE_EDGE = "KNOWLEDGE_EDGE"
    RED_FLAG = "RED_FLAG"
    CRITICAL_QUESTION = "CRITICAL_QUESTION"


class CitationDraft(APIModel):
    document_id: str
    chunk_id: str
    quote: str = Field(min_length=1)
    page: int = Field(ge=0)
    bounding_box: BoundingBox | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    source_confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def bbox_coordinates_are_ordered(self) -> CitationDraft:
        bbox = self.bounding_box
        if bbox and (bbox.x1 > bbox.x2 or bbox.y1 > bbox.y2):
            raise ValueError("Bounding box coordinates are not ordered")
        return self


class CitationValidationIssue(APIModel):
    code: str
    message: str
    field: str | None = None


class CitationValidationResult(APIModel):
    valid: bool
    citation: CitationDraft
    normalized_quote: str | None = None
    issues: list[CitationValidationIssue] = Field(default_factory=list)


class CitationView(CitationDraft):
    id: str
    owner_type: CitationOwnerType
    owner_id: str
    normalized_quote: str
    created_at: datetime

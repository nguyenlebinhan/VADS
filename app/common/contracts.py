from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )


DataT = TypeVar("DataT")


class ApiSuccessResponse(APIModel, Generic[DataT]):
    success: bool = True
    data: DataT
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class ApiErrorDetail(APIModel):
    code: str
    message: str
    details: Any = Field(default_factory=dict)


class ApiErrorResponse(APIModel):
    success: bool = False
    error: ApiErrorDetail
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class BoundingBox(APIModel):
    x1: float
    y1: float
    x2: float
    y2: float


class PageBlockContract(APIModel):
    id: str
    document_id: str
    page_index: int
    order_index: int
    block_type: str
    text: str
    normalized_text: str
    bbox: BoundingBox
    confidence: float | None = None
    source: str


class DocumentChunkContract(APIModel):
    id: str
    document_id: str
    section_id: str | None = None
    chunk_type: str
    content: str
    normalized_content: str
    chapter: str | None = None
    section: str | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    appendix: str | None = None
    form_code: str | None = None
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    start_block_id: str
    end_block_id: str
    bounding_boxes: list[dict[str, Any]] = Field(default_factory=list)
    ocr_confidence: float | None = None
    token_count: int


class DocumentStructureNode(APIModel):
    id: str
    parent_id: str | None = None
    section_type: str
    label: str | None = None
    title: str | None = None
    content: str
    hierarchy_level: int
    order_index: int
    page_start: int
    page_end: int
    start_block_id: str
    end_block_id: str
    heading_path: list[dict[str, Any]] = Field(default_factory=list)
    children: list[DocumentStructureNode] = Field(default_factory=list)


class SectionSearchFilters(APIModel):
    section_id: str | None = None
    chapter: str | None = None
    section: str | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    appendix: str | None = None
    form_code: str | None = None

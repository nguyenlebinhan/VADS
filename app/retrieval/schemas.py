from __future__ import annotations

from datetime import date as DateValue
from typing import Any

from pydantic import Field

from app.common.contracts import APIModel


class RetrievalFilters(APIModel):
    workspace_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    chapter: str | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    node_type: str | None = None
    agency: str | None = None
    date: DateValue | None = None
    language: str | None = None


class RetrievalRequest(APIModel):
    query: str = Field(min_length=1, max_length=4000)
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)
    mode: str = "HYBRID"


class RetrievedChunk(APIModel):
    chunk_id: str
    document_id: str
    workspace_id: str
    content: str
    score: float
    semantic_score: float
    keyword_score: float
    language: str
    chapter: str | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    entity_metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(APIModel):
    query: str
    limit: int
    items: list[RetrievedChunk]

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class VectorMetadataFilter:
    workspace_id: str | None = None
    document_ids: tuple[str, ...] = ()
    chapter: str | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    node_type: str | None = None
    agency: str | None = None
    issued_date: date | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingRecordInput:
    chunk_id: str
    document_id: str
    workspace_id: str
    vector: list[float]
    content: str
    normalized_content: str
    language: str
    chapter: str | None
    article: str | None
    clause: str | None
    point: str | None
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None
    printed_page_end: int | None
    entity_metadata: dict[str, Any] = field(default_factory=dict)
    embedding_model: str = "Vietnamese_Embedding"
    embedding_version: str = "1"
    node_type: str | None = None
    agency: str | None = None
    issued_date: date | None = None


@dataclass(frozen=True, slots=True)
class VectorSearchHit:
    record_id: str
    chunk_id: str
    document_id: str
    workspace_id: str
    content: str
    normalized_content: str
    score: float
    semantic_score: float
    keyword_score: float
    language: str
    chapter: str | None
    article: str | None
    clause: str | None
    point: str | None
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None
    printed_page_end: int | None
    entity_metadata: dict[str, Any]
    embedding_model: str
    embedding_version: str

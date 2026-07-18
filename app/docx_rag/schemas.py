from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DocxRagError(RuntimeError):
    """Base exception for the standalone DOCX RAG module."""


class NoDocxFilesError(DocxRagError):
    """Raised when the configured data directory has no DOCX files."""


class OpenAIConfigurationError(DocxRagError):
    """Raised when no supported OpenAI API key environment variable is set."""


class OpenAIRequestError(DocxRagError):
    """Raised when an OpenAI HTTP request fails or returns malformed data."""


class BlockKind(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE = "table"


class DocxBlock(BaseModel):
    file_name: str
    kind: BlockKind
    text: str
    paragraph_index: int | None = None
    table_index: int | None = None
    article: str | None = None
    clause: str | None = None
    page_number: int | None = None


class DocxChunk(BaseModel):
    chunk_id: str
    file_name: str
    text: str
    paragraph_indices: list[int] = Field(default_factory=list)
    table_indices: list[int] = Field(default_factory=list)
    article: str | None = None
    clause: str | None = None
    page_number: int | None = None


class SearchResult(BaseModel):
    chunk: DocxChunk
    score: float


class SourceCitation(BaseModel):
    file_name: str
    chunk_id: str
    paragraph_index: int | None = None
    table_index: int | None = None
    paragraph_indices: list[int] = Field(default_factory=list)
    table_indices: list[int] = Field(default_factory=list)
    article: str | None = None
    clause: str | None = None
    page_number: int | None = None
    quote: str
    score: float


class DocxRagResult(BaseModel):
    answer: str
    sources: list[SourceCitation]
    retrieval_mode: str
    page_note: str
    embedding_error: str | None = None


class DocxRagQueryResponse(BaseModel):
    query_id: str
    answer: str
    retrieval_mode: str
    sources_available: bool
    source_count: int = Field(ge=0)
    page_note: str
    embedding_error: str | None = None


class DocxRagSourcesResponse(BaseModel):
    query_id: str
    sources: list[SourceCitation]
    page_note: str


class DocxRagQuery(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    rebuild_index: bool = False

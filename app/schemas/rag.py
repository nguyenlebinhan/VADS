from pydantic import Field

from app.schemas.base import StrictAPIModel


class RagQueryRequest(StrictAPIModel):
    question: str = Field(min_length=1, max_length=8_000)
    document_ids: list[str] = Field(min_length=1, max_length=20)
    top_k: int = Field(default=5, ge=1, le=10)


class RagSourcePublic(StrictAPIModel):
    document_id: str
    document_title: str
    chunk_id: str
    page_number: int | None
    article: str | None
    clause: str | None
    quote: str
    score: float


class RagQueryResponse(StrictAPIModel):
    answer: str
    retrieval_mode: str
    sources: list[RagSourcePublic]

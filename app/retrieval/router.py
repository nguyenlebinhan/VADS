from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.retrieval.schemas import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
)
from app.retrieval.service import HybridRetrievalService
from app.vector_store.adapters.mock.embedding import DeterministicEmbeddingProvider
from app.vector_store.pgvector_store import PgVectorStore

router = APIRouter(tags=["Retrieval"])


def get_retrieval_service(
    session: Annotated[Session, Depends(get_db)],
) -> HybridRetrievalService:
    return HybridRetrievalService(
        vector_store=PgVectorStore(session),
        embedding_provider=DeterministicEmbeddingProvider(),
    )


@router.post(
    "/retrieval/search",
    response_model=ApiSuccessResponse[RetrievalResponse],
)
def search(
    payload: RetrievalRequest,
    service: Annotated[HybridRetrievalService, Depends(get_retrieval_service)],
) -> ApiSuccessResponse[RetrievalResponse]:
    hits = service.retrieve(
        payload.query,
        filters=payload.filters,
        semantic_only=payload.mode == "SEMANTIC",
    )
    return ApiSuccessResponse(
        data=RetrievalResponse(
            query=payload.query,
            limit=40 if len(payload.filters.document_ids) > 1 else 20,
            items=[RetrievedChunk.model_validate(hit) for hit in hits],
        )
    )

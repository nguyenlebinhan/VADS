from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.docx_rag.schemas import (
    DocxRagError,
    DocxRagQuery,
    DocxRagQueryResponse,
    DocxRagSourcesResponse,
    NoDocxFilesError,
    OpenAIConfigurationError,
    OpenAIRequestError,
)
from app.docx_rag.service import DocxRagService
from app.docx_rag.source_store import InMemorySourceStore, SourceStore

router = APIRouter(prefix="/docx-rag", tags=["DOCX RAG"])


@lru_cache(maxsize=1)
def get_docx_rag_service() -> DocxRagService:
    return DocxRagService()


@lru_cache(maxsize=1)
def get_source_store() -> SourceStore:
    return InMemorySourceStore()


@router.post("/query", response_model=DocxRagQueryResponse)
def query_docx_rag(
    body: DocxRagQuery,
    service: Annotated[DocxRagService, Depends(get_docx_rag_service)],
    source_store: Annotated[SourceStore, Depends(get_source_store)],
) -> DocxRagQueryResponse:
    query_id = str(uuid4())
    try:
        result = service.answer(
            body.question,
            top_k=body.top_k,
            force_rebuild=body.rebuild_index,
        )
        source_store.save(query_id, result.sources, result.page_note)
        return DocxRagQueryResponse(
            query_id=query_id,
            answer=result.answer,
            retrieval_mode=result.retrieval_mode,
            sources_available=bool(result.sources),
            source_count=len(result.sources),
            page_note=result.page_note,
            embedding_error=result.embedding_error,
        )
    except NoDocxFilesError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except OpenAIConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except OpenAIRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except (DocxRagError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get(
    "/queries/{query_id}/sources",
    response_model=DocxRagSourcesResponse,
)
def get_query_sources(
    query_id: str,
    source_store: Annotated[SourceStore, Depends(get_source_store)],
) -> DocxRagSourcesResponse:
    stored = source_store.get(query_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DOCX RAG query sources were not found or have expired",
        )
    return DocxRagSourcesResponse(
        query_id=query_id,
        sources=stored.sources,
        page_note=stored.page_note,
    )

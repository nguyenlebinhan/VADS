from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.documents.interfaces import SqlAlchemyDocumentChunkReader
from app.vector_store.adapters.document_context import Owner1DocumentContextAdapter
from app.vector_store.adapters.mock.embedding import DeterministicEmbeddingProvider
from app.vector_store.indexing import DocumentIndexingService
from app.vector_store.pgvector_store import PgVectorStore
from app.vector_store.schemas import IndexStatusData

router = APIRouter(tags=["Document Index"])


def get_indexing_service(session: Annotated[Session, Depends(get_db)]) -> DocumentIndexingService:
    return DocumentIndexingService(
        session,
        chunk_reader=SqlAlchemyDocumentChunkReader(session),
        context_reader=Owner1DocumentContextAdapter(session),
        embedding_provider=DeterministicEmbeddingProvider(),
        vector_store=PgVectorStore(session),
    )


@router.post(
    "/documents/{documentId}/index",
    response_model=ApiSuccessResponse[IndexStatusData],
    status_code=status.HTTP_202_ACCEPTED,
)
def index_document(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentIndexingService, Depends(get_indexing_service)],
) -> ApiSuccessResponse[IndexStatusData]:
    return ApiSuccessResponse(
        data=service.index_document(document_id),
        message="Đã lập chỉ mục tài liệu",
    )


@router.get(
    "/documents/{documentId}/index/status",
    response_model=ApiSuccessResponse[IndexStatusData],
)
def get_index_status(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentIndexingService, Depends(get_indexing_service)],
) -> ApiSuccessResponse[IndexStatusData]:
    return ApiSuccessResponse(data=service.get_status(document_id))


@router.post(
    "/documents/{documentId}/index/rebuild",
    response_model=ApiSuccessResponse[IndexStatusData],
    status_code=status.HTTP_202_ACCEPTED,
)
def rebuild_document_index(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentIndexingService, Depends(get_indexing_service)],
) -> ApiSuccessResponse[IndexStatusData]:
    return ApiSuccessResponse(
        data=service.index_document(document_id, rebuild=True),
        message="Đã xây dựng lại chỉ mục tài liệu",
    )

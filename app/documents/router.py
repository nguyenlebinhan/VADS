from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status
from sqlalchemy.orm import Session

from app.common.contracts import ApiSuccessResponse, DocumentChunkContract
from app.config.database import get_db
from app.config.settings import Settings, get_settings
from app.documents.schemas import (
    DocumentChunksData,
    DocumentData,
    DocumentDeleteData,
    DocumentPageDetail,
    DocumentPageSummary,
    DocumentSectionsData,
    DocumentUploadData,
    ProcessingStatusData,
)
from app.documents.service import DocumentQueryService
from app.model.schemas.documents import DocumentUploadResponse
from app.service.documents import DocumentService
from app.storage.provider import StorageProvider
from app.utils.storage_dependencies import get_object_storage
from app.utils.task_dispatcher import TaskDispatcher, get_task_dispatcher

router = APIRouter(tags=["Documents"])


def get_document_service(
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_object_storage)],
    dispatcher: Annotated[TaskDispatcher, Depends(get_task_dispatcher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    return DocumentService(session, storage=storage, dispatcher=dispatcher, settings=settings)


def get_query_service(session: Annotated[Session, Depends(get_db)]) -> DocumentQueryService:
    return DocumentQueryService(session)


@router.post(
    "/workspaces/{workspaceId}/documents",
    response_model=ApiSuccessResponse[DocumentUploadData],
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    workspace_id: Annotated[str, Path(alias="workspaceId", min_length=1, max_length=40)],
    file: Annotated[UploadFile, File(description="PDF or DOCX document")],
    service: Annotated[DocumentService, Depends(get_document_service)],
    display_name: Annotated[str | None, Form(alias="displayName", max_length=255)] = None,
) -> ApiSuccessResponse[DocumentUploadData]:
    result = service.upload(workspace_id, file, display_name=display_name)
    return ApiSuccessResponse(
        data=DocumentUploadData.model_validate(result), message="Tải tài liệu lên thành công"
    )


@router.get(
    "/documents/{documentId}",
    response_model=ApiSuccessResponse[DocumentData],
)
def get_document(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiSuccessResponse[DocumentData]:
    return ApiSuccessResponse(data=DocumentData.model_validate(service.get(document_id)))


@router.get(
    "/documents/{documentId}/status",
    response_model=ApiSuccessResponse[ProcessingStatusData],
)
def get_document_status(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiSuccessResponse[ProcessingStatusData]:
    return ApiSuccessResponse(
        data=ProcessingStatusData.model_validate(service.get_status(document_id))
    )


@router.get(
    "/documents/{documentId}/pages",
    response_model=ApiSuccessResponse[list[DocumentPageSummary]],
)
def list_document_pages(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentQueryService, Depends(get_query_service)],
) -> ApiSuccessResponse[list[DocumentPageSummary]]:
    return ApiSuccessResponse(data=service.list_pages(document_id))


@router.get(
    "/documents/{documentId}/pages/{pageIndex}",
    response_model=ApiSuccessResponse[DocumentPageDetail],
)
def get_document_page(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    page_index: Annotated[int, Path(alias="pageIndex", ge=0)],
    service: Annotated[DocumentQueryService, Depends(get_query_service)],
) -> ApiSuccessResponse[DocumentPageDetail]:
    return ApiSuccessResponse(data=service.get_page(document_id, page_index))


@router.get(
    "/documents/{documentId}/sections",
    response_model=ApiSuccessResponse[DocumentSectionsData],
)
def list_document_sections(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentQueryService, Depends(get_query_service)],
) -> ApiSuccessResponse[DocumentSectionsData]:
    return ApiSuccessResponse(
        data=DocumentSectionsData(document_id=document_id, items=service.list_sections(document_id))
    )


@router.get(
    "/documents/{documentId}/chunks",
    response_model=ApiSuccessResponse[DocumentChunksData],
)
def list_document_chunks(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentQueryService, Depends(get_query_service)],
) -> ApiSuccessResponse[DocumentChunksData]:
    return ApiSuccessResponse(
        data=DocumentChunksData(document_id=document_id, items=service.list_chunks(document_id))
    )


@router.get(
    "/documents/{documentId}/chunks/{chunkId}",
    response_model=ApiSuccessResponse[DocumentChunkContract],
)
def get_document_chunk(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    chunk_id: Annotated[str, Path(alias="chunkId", min_length=1, max_length=40)],
    service: Annotated[DocumentQueryService, Depends(get_query_service)],
) -> ApiSuccessResponse[DocumentChunkContract]:
    return ApiSuccessResponse(data=service.get_chunk(document_id, chunk_id))


@router.delete(
    "/documents/{documentId}",
    response_model=ApiSuccessResponse[DocumentDeleteData],
)
def delete_document(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiSuccessResponse[DocumentDeleteData]:
    result = service.soft_delete(document_id)
    return ApiSuccessResponse(
        data=DocumentDeleteData.model_validate(result),
        message="Xoá tài liệu thành công",
    )


@router.post(
    "/documents/{documentId}/reprocess",
    response_model=ApiSuccessResponse[DocumentUploadData],
    status_code=status.HTTP_202_ACCEPTED,
)
def reprocess_document(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiSuccessResponse[DocumentUploadData]:
    result: DocumentUploadResponse = service.reprocess(document_id)
    return ApiSuccessResponse(
        data=DocumentUploadData.model_validate(result),
        message="Đã tạo processing job mới",
    )

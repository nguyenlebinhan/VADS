from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import Settings, get_settings
from app.core.audit import RequestMetadata
from app.core.permissions import Permission, UserRole
from app.database.async_session import get_async_db
from app.dependencies.permissions import require_permission
from app.exceptions import AuthorizationError, NotFoundError
from app.model.documents import Document
from app.model.workspaces import Workspace, WorkspaceStatus
from app.model.users import User
from app.schemas.document import DocumentPublic, DocumentUploadPublic, document_to_public
from app.service.documents import DocumentService
from app.services.document_service import SecureDocumentService
from app.storage.provider import StorageProvider
from app.utils.storage_dependencies import get_object_storage
from app.utils.task_dispatcher import TaskDispatcher, get_task_dispatcher

router = APIRouter(prefix="/documents", tags=["Secure documents"])


def _personal_workspace(session: Session, actor: User) -> Workspace:
    workspace = session.scalar(
        select(Workspace)
        .where(
            Workspace.owner_id == actor.id,
            Workspace.status == WorkspaceStatus.ACTIVE,
            Workspace.deleted_at.is_(None),
        )
        .order_by(Workspace.created_at)
        .limit(1)
    )
    if workspace is not None:
        return workspace
    workspace = Workspace(
        name=f"Tai lieu cua {actor.full_name}",
        owner_id=actor.id,
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace


def _owned_document(session: Session, actor: User, document_id: str) -> Document:
    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == actor.id,
            Document.is_deleted.is_(False),
            Document.deleted_at.is_(None),
        )
    )
    if document is None:
        raise NotFoundError("DOCUMENT", document_id)
    return document


@router.post("", response_model=DocumentUploadPublic, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File(description="PDF or DOCX document")],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_CREATE))],
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_object_storage)],
    dispatcher: Annotated[TaskDispatcher, Depends(get_task_dispatcher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentUploadPublic:
    if actor.role == UserRole.USER and not settings.user_document_upload_enabled:
        raise AuthorizationError(
            code="DOCUMENT_UPLOAD_DISABLED",
            message="Chuc nang tai tai lieu cua nguoi dung dang bi tat.",
        )
    workspace = _personal_workspace(session, actor)
    result = DocumentService(
        session,
        storage=storage,
        dispatcher=dispatcher,
        settings=settings,
    ).upload(
        workspace.id,
        file,
        uploaded_by=actor.id,
        commune_id=actor.commune_id,
        owner_id=actor.id,
    )
    return DocumentUploadPublic(
        document_id=result.document_id,
        workspace_id=result.workspace_id,
        status=result.status,
        progress=result.progress,
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentUploadPublic,
    status_code=status.HTTP_202_ACCEPTED,
)
def reprocess_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_CREATE))],
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_object_storage)],
    dispatcher: Annotated[TaskDispatcher, Depends(get_task_dispatcher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentUploadPublic:
    _owned_document(session, actor, document_id)
    result = DocumentService(
        session,
        storage=storage,
        dispatcher=dispatcher,
        settings=settings,
    ).reprocess(document_id)
    return DocumentUploadPublic(
        document_id=result.document_id,
        workspace_id=result.workspace_id,
        status=result.status,
        progress=result.progress,
    )


@router.get("", response_model=list[DocumentPublic])
async def list_documents(
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DocumentPublic]:
    documents = await SecureDocumentService(session).list_visible(
        actor=actor,
        offset=offset,
        limit=limit,
    )
    return [document_to_public(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentPublic)
async def get_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> DocumentPublic:
    document = await SecureDocumentService(session).get_visible(
        actor=actor,
        document_id=document_id,
        request=RequestMetadata.from_request(request),
    )
    return document_to_public(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_DELETE_OWN))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> Response:
    await SecureDocumentService(session).soft_delete(
        actor=actor,
        document_id=document_id,
        request=RequestMetadata.from_request(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/restore", response_model=DocumentPublic)
async def restore_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_RESTORE_COMMUNE))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> DocumentPublic:
    document = await SecureDocumentService(session).restore(
        actor=actor,
        document_id=document_id,
        request=RequestMetadata.from_request(request),
    )
    return document_to_public(document)


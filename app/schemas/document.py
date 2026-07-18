from datetime import datetime

from app.model.documents import Document, DocumentApprovalStatus
from app.model.processing import ProcessingStatus
from app.schemas.base import StrictAPIModel


class DocumentPublic(StrictAPIModel):
    id: str
    commune_id: str
    owner_id: str | None
    title: str
    status: ProcessingStatus
    approval_status: DocumentApprovalStatus
    meeting_id: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class DocumentUploadPublic(StrictAPIModel):
    document_id: str
    workspace_id: str
    status: ProcessingStatus
    progress: int


def document_to_public(document: Document) -> DocumentPublic:
    return DocumentPublic(
        id=document.id,
        commune_id=document.commune_id,
        owner_id=document.owner_id,
        title=document.display_name,
        status=document.status,
        approval_status=document.approval_status,
        meeting_id=document.meeting_id,
        is_deleted=document.is_deleted,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.model.documents import DocumentType
from app.model.processing import ProcessingStatus, ProcessingStep
from app.model.schemas.base import APIModel


class DocumentUploadResponse(APIModel):
    document_id: str
    workspace_id: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: ProcessingStep


class DocumentResponse(APIModel):
    document_id: str
    workspace_id: str
    display_name: str
    original_filename: str
    mime_type: str
    file_extension: str
    file_size: int
    checksum: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: ProcessingStep
    total_pages: int | None = None
    document_type: DocumentType | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDeleteResponse(APIModel):
    document_id: str
    status: Literal["DELETED"] = "DELETED"

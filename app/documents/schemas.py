from datetime import datetime

from pydantic import Field

from app.common.contracts import (
    APIModel,
    DocumentChunkContract,
    DocumentStructureNode,
    PageBlockContract,
)
from app.model.documents import DocumentType
from app.model.processing import ProcessingStatus, ProcessingStep


class DocumentUploadData(APIModel):
    document_id: str
    workspace_id: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: ProcessingStep


class DocumentData(DocumentUploadData):
    display_name: str
    original_filename: str
    mime_type: str
    file_extension: str
    file_size: int
    checksum: str
    total_pages: int | None = None
    document_type: DocumentType | None = None
    created_at: datetime
    updated_at: datetime


class ProcessingStatusData(APIModel):
    document_id: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: ProcessingStep
    current_page: int | None = Field(default=None, ge=0)
    total_pages: int | None = Field(default=None, ge=0)
    message: str
    started_at: datetime | None = None
    updated_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class DocumentPageSummary(APIModel):
    id: str
    document_id: str
    page_index: int
    printed_page_number: int | None = None
    width: float
    height: float
    rotation: int
    has_text_layer: bool
    image_only: bool
    needs_ocr: bool
    ocr_confidence: float | None = None
    block_count: int


class DocumentPageDetail(DocumentPageSummary):
    extracted_text: str
    rendered_object_key: str | None = None
    blocks: list[PageBlockContract] = Field(default_factory=list)


class DocumentDeleteData(APIModel):
    document_id: str
    status: str = "DELETED"


class DocumentSectionsData(APIModel):
    document_id: str
    items: list[DocumentStructureNode]


class DocumentChunksData(APIModel):
    document_id: str
    items: list[DocumentChunkContract]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)

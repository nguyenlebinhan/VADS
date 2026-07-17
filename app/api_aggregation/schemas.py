from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.contracts import APIModel, DocumentStructureNode


class DashboardDocument(APIModel):
    id: str
    display_name: str
    status: str
    progress: float
    total_pages: int | None = None
    index_status: str | None = None
    updated_at: datetime


class WorkspaceDashboardData(APIModel):
    workspace_id: str
    document_count: int
    processing_count: int
    completed_count: int
    indexed_count: int
    documents: list[DashboardDocument]


class ViewerPageData(APIModel):
    page_index: int
    printed_page_number: int | None = None
    width: float
    height: float
    image_url: str | None = None


class ChunkLocationData(APIModel):
    chunk_id: str
    section_id: str | None = None
    pdf_page_start: int
    pdf_page_end: int
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    bounding_boxes: list[dict[str, Any]] = Field(default_factory=list)


class ViewerData(APIModel):
    document: dict[str, Any]
    pages: list[ViewerPageData]
    section_tree: list[DocumentStructureNode]
    chunk_locations: list[ChunkLocationData]


class AnalysisOverviewData(APIModel):
    document_id: str
    summary: dict[str, Any] | None = None
    graph_statistics: dict[str, Any]
    red_flags: list[dict[str, Any]]
    critical_questions: list[dict[str, Any]]
    processing_status: dict[str, Any] | None = None
    index_status: dict[str, Any] | None = None

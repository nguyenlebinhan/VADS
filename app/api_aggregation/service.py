from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_aggregation.adapters.owner1 import Owner1ReadAdapter
from app.api_aggregation.contracts import (
    CriticalQuestionReader,
    KnowledgeGraphReader,
    PageImageUrlSigner,
    RedFlagReader,
    SummaryReader,
)
from app.api_aggregation.schemas import (
    AnalysisOverviewData,
    ChunkLocationData,
    DashboardDocument,
    ViewerData,
    ViewerPageData,
    WorkspaceDashboardData,
)
from app.exceptions import NotFoundError
from app.model.processing import ProcessingJob
from app.service.processing import ProcessingStateService
from app.vector_store.models import DocumentIndexJob


class ApiAggregationService:
    def __init__(
        self,
        session: Session,
        *,
        summary_reader: SummaryReader,
        graph_reader: KnowledgeGraphReader,
        red_flag_reader: RedFlagReader,
        critical_question_reader: CriticalQuestionReader,
        page_signer: PageImageUrlSigner,
    ) -> None:
        self.session = session
        self.owner1 = Owner1ReadAdapter(session)
        self.summary_reader = summary_reader
        self.graph_reader = graph_reader
        self.red_flag_reader = red_flag_reader
        self.critical_question_reader = critical_question_reader
        self.page_signer = page_signer

    def dashboard(self, workspace_id: str) -> WorkspaceDashboardData:
        documents = self.owner1.list_workspace_documents(workspace_id)
        items: list[DashboardDocument] = []
        for document in documents:
            processing = self._latest_processing(document.id)
            index_job = self._latest_index(document.id)
            items.append(
                DashboardDocument(
                    id=document.id,
                    display_name=document.display_name,
                    status=(processing.status.value if processing else document.status.value),
                    progress=float(processing.progress if processing else 0),
                    total_pages=document.total_pages,
                    index_status=index_job.status.value if index_job else None,
                    updated_at=document.updated_at,
                )
            )
        return WorkspaceDashboardData(
            workspace_id=workspace_id,
            document_count=len(items),
            processing_count=sum(item.status in {"QUEUED", "PROCESSING"} for item in items),
            completed_count=sum(item.status == "COMPLETED" for item in items),
            indexed_count=sum(item.index_status == "COMPLETED" for item in items),
            documents=items,
        )

    def viewer_data(self, document_id: str) -> ViewerData:
        document = self.owner1.get_document(document_id)
        if document is None:
            raise NotFoundError("DOCUMENT", document_id)
        pages = self.owner1.extraction.list_pages(document_id)
        structures = self.owner1.chunks.get_document_structure(document_id)
        chunks = self.owner1.chunks.list_chunks(document_id)
        return ViewerData(
            document={
                "id": document.id,
                "workspaceId": document.workspace_id,
                "displayName": document.display_name,
                "originalFilename": document.original_filename,
                "mimeType": document.mime_type,
                "totalPages": document.total_pages,
                "status": document.status.value,
            },
            pages=[
                ViewerPageData(
                    page_index=page.page_index,
                    printed_page_number=page.printed_page_number,
                    width=page.width,
                    height=page.height,
                    image_url=(
                        self.page_signer.sign_page_image(page.rendered_object_key)
                        if page.rendered_object_key
                        else None
                    ),
                )
                for page in pages
            ],
            section_tree=structures,
            chunk_locations=[
                ChunkLocationData(
                    chunk_id=chunk.id,
                    section_id=chunk.section_id,
                    pdf_page_start=chunk.pdf_page_start,
                    pdf_page_end=chunk.pdf_page_end,
                    article=chunk.article,
                    clause=chunk.clause,
                    point=chunk.point,
                    bounding_boxes=chunk.bounding_boxes,
                )
                for chunk in chunks
            ],
        )

    def analysis_overview(self, document_id: str) -> AnalysisOverviewData:
        if self.owner1.get_document(document_id) is None:
            raise NotFoundError("DOCUMENT", document_id)
        graph = self.graph_reader.get_graph_overview(document_id)
        processing = self._latest_processing(document_id)
        index_job = self._latest_index(document_id)
        return AnalysisOverviewData(
            document_id=document_id,
            summary=self.summary_reader.get_latest_summary(document_id),
            graph_statistics=graph.get("statistics", {}),
            red_flags=self.red_flag_reader.list_red_flags(document_id),
            critical_questions=self.critical_question_reader.list_critical_questions(document_id),
            processing_status=(
                ProcessingStateService.to_response(processing).model_dump(
                    by_alias=True, mode="json"
                )
                if processing
                else None
            ),
            index_status=(
                {
                    "status": index_job.status.value,
                    "progress": index_job.progress,
                    "indexedChunks": index_job.indexed_chunks,
                    "totalChunks": index_job.total_chunks,
                }
                if index_job
                else None
            ),
        )

    def _latest_processing(self, document_id: str) -> ProcessingJob | None:
        return self.session.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.attempt.desc())
            .limit(1)
        )

    def _latest_index(self, document_id: str) -> DocumentIndexJob | None:
        return self.session.scalar(
            select(DocumentIndexJob)
            .where(DocumentIndexJob.document_id == document_id)
            .order_by(DocumentIndexJob.attempt.desc())
            .limit(1)
        )

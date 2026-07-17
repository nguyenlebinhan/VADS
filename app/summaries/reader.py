from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.citations.reader import CitationReader, SqlAlchemyCitationReader
from app.citations.schemas import CitationOwnerType
from app.summaries.models import DocumentSummary
from app.summaries.repository import SummaryRepository
from app.summaries.schemas import DocumentSummaryView, SummaryItemView


class SummaryReader(Protocol):
    def list_for_document(self, document_id: str) -> list[DocumentSummaryView]: ...

    def get_summary(self, summary_id: str) -> DocumentSummaryView | None: ...

    def get_latest(self, document_id: str) -> DocumentSummaryView | None: ...


class SqlAlchemySummaryReader:
    def __init__(self, session: Session, citation_reader: CitationReader | None = None) -> None:
        self.repository = SummaryRepository(session)
        self.citation_reader = citation_reader or SqlAlchemyCitationReader(session)

    def list_for_document(self, document_id: str) -> list[DocumentSummaryView]:
        return [self._view(summary) for summary in self.repository.list_for_document(document_id)]

    def get_summary(self, summary_id: str) -> DocumentSummaryView | None:
        summary = self.repository.get(summary_id)
        return self._view(summary) if summary else None

    def get_latest(self, document_id: str) -> DocumentSummaryView | None:
        summary = self.repository.get_latest(document_id)
        return self._view(summary) if summary else None

    def _view(self, summary: DocumentSummary) -> DocumentSummaryView:
        items = []
        for item in self.repository.list_items(summary.id):
            items.append(
                SummaryItemView(
                    id=item.id,
                    category=item.category,
                    title=item.title,
                    content=item.content,
                    importance=item.importance,
                    confidence=item.confidence,
                    status=item.status,
                    orderIndex=item.order_index,
                    systemMetadata=item.system_metadata,
                    citations=self.citation_reader.list_for_owner(
                        CitationOwnerType.SUMMARY_ITEM,
                        item.id,
                    ),
                )
            )
        return DocumentSummaryView(
            id=summary.id,
            documentId=summary.document_id,
            workflowId=summary.workflow_id,
            version=summary.version,
            modelName=summary.model_name,
            promptVersion=summary.prompt_version,
            status=summary.status,
            isCurrent=summary.is_current,
            createdAt=summary.created_at,
            updatedAt=summary.updated_at,
            items=items,
        )

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.summaries.models import DocumentSummary, SummaryItem
from app.summaries.schemas import SummaryItemDraft, SummaryItemStatus, SummaryStatus


class SummaryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_version(self, document_id: str) -> int:
        statement = select(func.max(DocumentSummary.version)).where(
            DocumentSummary.document_id == document_id
        )
        return int(self.session.scalar(statement) or 0) + 1

    def create_version(
        self,
        *,
        document_id: str,
        workflow_id: str,
        model_name: str,
        prompt_version: str,
        status: SummaryStatus,
        rejected_item_count: int = 0,
    ) -> DocumentSummary:
        for previous in self.list_for_document(document_id):
            if previous.is_current:
                previous.is_current = False
                if previous.status == SummaryStatus.COMPLETED.value:
                    previous.status = SummaryStatus.SUPERSEDED.value
        summary = DocumentSummary(
            document_id=document_id,
            workflow_id=workflow_id,
            version=self.next_version(document_id),
            model_name=model_name,
            prompt_version=prompt_version,
            status=status.value,
            is_current=True,
            rejected_item_count=rejected_item_count,
        )
        self.session.add(summary)
        self.session.flush()
        return summary

    def add_item(
        self,
        summary_id: str,
        draft: SummaryItemDraft,
        *,
        order_index: int,
    ) -> SummaryItem:
        item = SummaryItem(
            summary_id=summary_id,
            category=draft.category.value,
            title=draft.title,
            content=draft.content,
            importance=draft.importance.value,
            confidence=draft.confidence,
            status=SummaryItemStatus.PUBLISHED.value,
            order_index=order_index,
            system_metadata=draft.system_metadata,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def get(self, summary_id: str) -> DocumentSummary | None:
        return self.session.get(DocumentSummary, summary_id)

    def list_for_document(self, document_id: str) -> list[DocumentSummary]:
        statement = (
            select(DocumentSummary)
            .where(DocumentSummary.document_id == document_id)
            .order_by(DocumentSummary.version.desc())
        )
        return list(self.session.scalars(statement))

    def get_latest(self, document_id: str) -> DocumentSummary | None:
        statement = (
            select(DocumentSummary)
            .where(
                DocumentSummary.document_id == document_id,
                DocumentSummary.is_current.is_(True),
            )
            .order_by(DocumentSummary.version.desc())
        )
        return self.session.scalar(statement)

    def list_items(self, summary_id: str) -> list[SummaryItem]:
        statement = (
            select(SummaryItem)
            .where(SummaryItem.summary_id == summary_id)
            .order_by(SummaryItem.order_index)
        )
        return list(self.session.scalars(statement))

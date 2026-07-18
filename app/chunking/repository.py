from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.model.chunking import DocumentChunk
from app.model.extraction import DocumentPage, PageBlock
from app.model.structure import DocumentSection


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_document(self, document_id: str) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.order_index)
        )
        return list(self.session.scalars(statement))

    def list_page(
        self,
        document_id: str,
        *,
        page: int,
        page_size: int,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.order_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement))

    def count_for_document(self, document_id: str) -> int:
        statement = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        return self.session.scalar(statement) or 0

    def get(self, chunk_id: str) -> DocumentChunk | None:
        return self.session.get(DocumentChunk, chunk_id)

    def search(self, document_id: str, filters: dict[str, str | None]) -> list[DocumentChunk]:
        statement = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        allowed = {
            "section_id",
            "chapter",
            "section",
            "article",
            "clause",
            "point",
            "appendix",
            "form_code",
        }
        for field, value in filters.items():
            if field in allowed and value is not None:
                statement = statement.where(getattr(DocumentChunk, field) == value)
        return list(self.session.scalars(statement.order_by(DocumentChunk.order_index)))


class ExtractionReadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_pages(self, document_id: str) -> list[DocumentPage]:
        statement = (
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .options(selectinload(DocumentPage.blocks))
            .order_by(DocumentPage.page_index)
        )
        return list(self.session.scalars(statement))

    def get_page(self, document_id: str, page_index: int) -> DocumentPage | None:
        statement = (
            select(DocumentPage)
            .where(
                DocumentPage.document_id == document_id,
                DocumentPage.page_index == page_index,
            )
            .options(selectinload(DocumentPage.blocks))
        )
        return self.session.scalar(statement)

    def get_page_blocks(self, document_id: str, page_index: int) -> list[PageBlock]:
        page = self.get_page(document_id, page_index)
        return list(page.blocks) if page else []


class StructureRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_document(self, document_id: str) -> list[DocumentSection]:
        statement = (
            select(DocumentSection)
            .where(DocumentSection.document_id == document_id)
            .order_by(DocumentSection.order_index)
        )
        return list(self.session.scalars(statement))

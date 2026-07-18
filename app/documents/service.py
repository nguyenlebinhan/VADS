from sqlalchemy.orm import Session

from app.chunking.reader import SqlAlchemyDocumentChunkReader
from app.chunking.repository import ExtractionReadRepository
from app.common.contracts import DocumentChunkContract, DocumentStructureNode
from app.documents.schemas import DocumentPageDetail, DocumentPageSummary
from app.exceptions import NotFoundError
from app.model.extraction import DocumentPage
from app.model.repositories.documents import DocumentRepository


class DocumentQueryService:
    def __init__(self, session: Session) -> None:
        self.documents = DocumentRepository(session)
        self.extraction = ExtractionReadRepository(session)
        self.reader = SqlAlchemyDocumentChunkReader(session)

    def list_pages(self, document_id: str) -> list[DocumentPageSummary]:
        self._ensure_document(document_id)
        return [self._page_summary(page) for page in self.extraction.list_pages(document_id)]

    def get_page(self, document_id: str, page_index: int) -> DocumentPageDetail:
        self._ensure_document(document_id)
        page = self.extraction.get_page(document_id, page_index)
        if page is None:
            raise NotFoundError("DOCUMENT_PAGE", f"{document_id}:{page_index}")
        blocks = self.reader.get_page_blocks(document_id, page_index)
        return DocumentPageDetail(
            **self._page_summary(page).model_dump(),
            extracted_text=page.extracted_text,
            rendered_object_key=page.rendered_object_key,
            blocks=blocks,
        )

    def list_sections(self, document_id: str) -> list[DocumentStructureNode]:
        self._ensure_document(document_id)
        return self.reader.get_document_structure(document_id)

    def list_chunks(
        self,
        document_id: str,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[DocumentChunkContract], int]:
        self._ensure_document(document_id)
        return self.reader.list_chunks_page(document_id, page=page, page_size=page_size)

    def get_chunk(self, document_id: str, chunk_id: str) -> DocumentChunkContract:
        self._ensure_document(document_id)
        chunk = self.reader.get_chunk(chunk_id)
        if chunk.document_id != document_id:
            raise NotFoundError("CHUNK", chunk_id)
        return chunk

    def _ensure_document(self, document_id: str) -> None:
        if self.documents.get_active(document_id) is None:
            raise NotFoundError("DOCUMENT", document_id)

    @staticmethod
    def _page_summary(page: DocumentPage) -> DocumentPageSummary:
        return DocumentPageSummary(
            id=page.id,
            document_id=page.document_id,
            page_index=page.page_index,
            printed_page_number=page.printed_page_number,
            width=page.width,
            height=page.height,
            rotation=page.rotation,
            has_text_layer=page.has_text_layer,
            image_only=page.image_only,
            needs_ocr=page.needs_ocr,
            ocr_confidence=page.ocr_confidence,
            block_count=len(page.blocks),
        )


# Stable import for modules that integrated against the original service path.
from app.service.documents import DocumentService  # noqa: E402

__all__ = ["DocumentQueryService", "DocumentService"]

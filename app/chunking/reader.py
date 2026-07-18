from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.chunking.repository import ChunkRepository, ExtractionReadRepository, StructureRepository
from app.common.contracts import (
    DocumentChunkContract,
    DocumentStructureNode,
    PageBlockContract,
    SectionSearchFilters,
)
from app.exceptions import NotFoundError
from app.model.chunking import DocumentChunk
from app.model.extraction import PageBlock
from app.model.structure import DocumentSection


class DocumentChunkReader(Protocol):
    def list_chunks(self, document_id: str) -> list[DocumentChunkContract]: ...

    def get_chunk(self, chunk_id: str) -> DocumentChunkContract: ...

    def search_chunks_by_section(
        self,
        document_id: str,
        filters: SectionSearchFilters,
    ) -> list[DocumentChunkContract]: ...

    def get_page_blocks(
        self,
        document_id: str,
        page_index: int,
    ) -> list[PageBlockContract]: ...

    def get_document_structure(self, document_id: str) -> list[DocumentStructureNode]: ...


class SqlAlchemyDocumentChunkReader:
    def __init__(self, session: Session) -> None:
        self.chunk_repository = ChunkRepository(session)
        self.extraction_repository = ExtractionReadRepository(session)
        self.structure_repository = StructureRepository(session)

    def list_chunks(self, document_id: str) -> list[DocumentChunkContract]:
        return [
            self._chunk_contract(chunk)
            for chunk in self.chunk_repository.list_for_document(document_id)
        ]

    def list_chunks_page(
        self,
        document_id: str,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[DocumentChunkContract], int]:
        chunks = self.chunk_repository.list_page(
            document_id,
            page=page,
            page_size=page_size,
        )
        return (
            [self._chunk_contract(chunk) for chunk in chunks],
            self.chunk_repository.count_for_document(document_id),
        )

    def get_chunk(self, chunk_id: str) -> DocumentChunkContract:
        chunk = self.chunk_repository.get(chunk_id)
        if chunk is None:
            raise NotFoundError("CHUNK", chunk_id)
        return self._chunk_contract(chunk)

    def search_chunks_by_section(
        self,
        document_id: str,
        filters: SectionSearchFilters,
    ) -> list[DocumentChunkContract]:
        raw_filters = filters.model_dump(exclude_none=True)
        return [
            self._chunk_contract(chunk)
            for chunk in self.chunk_repository.search(document_id, raw_filters)
        ]

    def get_page_blocks(
        self,
        document_id: str,
        page_index: int,
    ) -> list[PageBlockContract]:
        return [
            self._block_contract(block, page_index)
            for block in self.extraction_repository.get_page_blocks(document_id, page_index)
        ]

    def get_document_structure(self, document_id: str) -> list[DocumentStructureNode]:
        sections = self.structure_repository.list_for_document(document_id)
        nodes = {section.id: self._section_contract(section) for section in sections}
        roots: list[DocumentStructureNode] = []
        for section in sections:
            node = nodes[section.id]
            if section.parent_id and section.parent_id in nodes:
                nodes[section.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    @staticmethod
    def _chunk_contract(chunk: DocumentChunk) -> DocumentChunkContract:
        return DocumentChunkContract.model_validate(chunk)

    @staticmethod
    def _block_contract(block: PageBlock, page_index: int) -> PageBlockContract:
        return PageBlockContract(
            id=block.id,
            document_id=block.document_id,
            page_index=page_index,
            order_index=block.order_index,
            block_type=block.block_type,
            text=block.text,
            normalized_text=block.normalized_text,
            bbox=block.bbox,
            confidence=block.confidence,
            source=block.source,
        )

    @staticmethod
    def _section_contract(section: DocumentSection) -> DocumentStructureNode:
        return DocumentStructureNode(
            id=section.id,
            parent_id=section.parent_id,
            section_type=section.section_type.value,
            label=section.label,
            title=section.title,
            content=section.content,
            hierarchy_level=section.hierarchy_level,
            order_index=section.order_index,
            page_start=section.page_start,
            page_end=section.page_end,
            start_block_id=section.start_block_id,
            end_block_id=section.end_block_id,
            heading_path=section.heading_path,
        )

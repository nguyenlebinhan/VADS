from __future__ import annotations

from app.common.contracts import (
    DocumentChunkContract,
    DocumentStructureNode,
    PageBlockContract,
    SectionSearchFilters,
)


class SnapshotDocumentChunkReader:
    """Immutable reader used by parallel workflow steps after one database read."""

    def __init__(self, chunks: list[DocumentChunkContract]) -> None:
        self._chunks = list(chunks)
        self._by_id = {chunk.id: chunk for chunk in chunks}

    def list_chunks(self, document_id: str) -> list[DocumentChunkContract]:
        return [chunk for chunk in self._chunks if chunk.document_id == document_id]

    def get_chunk(self, chunk_id: str) -> DocumentChunkContract:
        try:
            return self._by_id[chunk_id]
        except KeyError as exc:
            raise KeyError(f"Chunk not found: {chunk_id}") from exc

    def search_chunks_by_section(
        self,
        document_id: str,
        filters: SectionSearchFilters,
    ) -> list[DocumentChunkContract]:
        values = filters.model_dump(exclude_none=True)
        return [
            chunk
            for chunk in self.list_chunks(document_id)
            if all(getattr(chunk, key) == value for key, value in values.items())
        ]

    def get_page_blocks(self, document_id: str, page_index: int) -> list[PageBlockContract]:
        del document_id, page_index
        return []

    def get_document_structure(self, document_id: str) -> list[DocumentStructureNode]:
        del document_id
        return []

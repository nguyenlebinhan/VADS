from typing import Protocol

from app.vector_store.contracts import (
    EmbeddingRecordInput,
    VectorMetadataFilter,
    VectorSearchHit,
)


class VectorStore(Protocol):
    def upsert_chunks(self, records: list[EmbeddingRecordInput]) -> int: ...

    def delete_document(self, document_id: str) -> int: ...

    def similarity_search(
        self,
        query_vector: list[float],
        *,
        filters: VectorMetadataFilter,
        limit: int,
    ) -> list[VectorSearchHit]: ...

    def hybrid_search(
        self,
        query_vector: list[float],
        query_text: str,
        *,
        filters: VectorMetadataFilter,
        limit: int,
    ) -> list[VectorSearchHit]: ...

    def health_check(self) -> bool: ...

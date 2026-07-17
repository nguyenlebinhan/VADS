from app.retrieval.schemas import RetrievalFilters
from app.vector_store.contracts import VectorMetadataFilter, VectorSearchHit
from app.vector_store.embedding import (
    MULTILINGUAL_EMBEDDING_MODEL,
    VIETNAMESE_EMBEDDING_MODEL,
    EmbeddingProvider,
)
from app.vector_store.interfaces import VectorStore


class HybridRetrievalService:
    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    def retrieve(
        self,
        query: str,
        *,
        filters: RetrievalFilters,
        semantic_only: bool = False,
    ) -> list[VectorSearchHit]:
        limit = 40 if len(filters.document_ids) > 1 else 20
        model_alias = (
            VIETNAMESE_EMBEDDING_MODEL
            if self._is_vietnamese(query)
            else MULTILINGUAL_EMBEDDING_MODEL
        )
        vector = self.embedding_provider.embed_query(query, model_alias=model_alias)
        metadata = VectorMetadataFilter(
            workspace_id=filters.workspace_id,
            document_ids=tuple(filters.document_ids),
            chapter=filters.chapter,
            article=filters.article,
            clause=filters.clause,
            point=filters.point,
            node_type=filters.node_type,
            agency=filters.agency,
            issued_date=filters.date,
            language=filters.language,
        )
        if semantic_only:
            return self.vector_store.similarity_search(vector, filters=metadata, limit=limit)
        return self.vector_store.hybrid_search(
            vector,
            query,
            filters=metadata,
            limit=limit,
        )

    @staticmethod
    def _is_vietnamese(value: str) -> bool:
        lowered = value.casefold()
        markers = ("đ", "ă", "â", "ê", "ô", "ơ", "ư", "điều", "khoản", "thời hạn")
        return any(marker in lowered for marker in markers)

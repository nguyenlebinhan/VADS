from __future__ import annotations

from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.contracts import DocumentChunkContract
from app.retrieval.schemas import RetrievalFilters
from app.retrieval.service import HybridRetrievalService
from app.vector_store.adapters.document_context import DocumentContext
from app.vector_store.adapters.mock.embedding import DeterministicEmbeddingProvider
from app.vector_store.contracts import EmbeddingRecordInput, VectorMetadataFilter
from app.vector_store.indexing import DocumentIndexingService
from app.vector_store.models import DocumentIndexJob, EmbeddingRecord, IndexStatus
from app.vector_store.pgvector_store import PgVectorStore


class ChunkReaderStub:
    def __init__(self, chunks: list[DocumentChunkContract]) -> None:
        self.chunks = chunks

    def list_chunks(self, document_id: str) -> list[DocumentChunkContract]:
        return [chunk for chunk in self.chunks if chunk.document_id == document_id]


class ContextReaderStub:
    def get_context(self, document_id: str) -> DocumentContext | None:
        if document_id == "missing":
            return None
        return DocumentContext(document_id=document_id, workspace_id="workspace-1")


def chunk(chunk_id: str = "chunk-1", document_id: str = "document-1") -> DocumentChunkContract:
    return DocumentChunkContract(
        id=chunk_id,
        document_id=document_id,
        section_id="section-1",
        chunk_type="LEGAL_CLAUSE",
        content="Điều 3. Thời hạn phê duyệt quyết toán là 30 ngày.",
        normalized_content="điều 3 thời hạn phê duyệt quyết toán là 30 ngày",
        chapter="Chương I",
        article="Điều 3",
        clause="Khoản 2",
        point=None,
        pdf_page_start=13,
        pdf_page_end=13,
        printed_page_start=14,
        printed_page_end=14,
        start_block_id="block-1",
        end_block_id="block-2",
        bounding_boxes=[{"pageIndex": 13, "x1": 10, "y1": 20, "x2": 90, "y2": 42}],
        ocr_confidence=0.98,
        token_count=18,
    )


def record(
    provider: DeterministicEmbeddingProvider,
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "document-1",
    article: str = "Điều 3",
    content: str = "Điều 3. Thời hạn phê duyệt quyết toán là 30 ngày.",
) -> EmbeddingRecordInput:
    vector = provider.embed_query(content, model_alias="Vietnamese_Embedding")
    return EmbeddingRecordInput(
        chunk_id=chunk_id,
        document_id=document_id,
        workspace_id="workspace-1",
        vector=vector,
        content=content,
        normalized_content=content.casefold(),
        language="vi",
        chapter="Chương I",
        article=article,
        clause="Khoản 2",
        point=None,
        pdf_page_start=13,
        pdf_page_end=13,
        printed_page_start=14,
        printed_page_end=14,
        entity_metadata={"boundingBoxes": [{"pageIndex": 13, "x1": 10, "y1": 20}]},
        embedding_model="Vietnamese_Embedding",
        embedding_version="mock-hash-v1",
    )


def test_index_and_rebuild_document(db_session: Session) -> None:
    provider = DeterministicEmbeddingProvider()
    store = PgVectorStore(db_session)
    service = DocumentIndexingService(
        db_session,
        chunk_reader=ChunkReaderStub([chunk()]),
        context_reader=ContextReaderStub(),
        embedding_provider=provider,
        vector_store=store,
    )

    first = service.index_document("document-1")
    rebuilt = service.index_document("document-1", rebuild=True)

    assert first.status == IndexStatus.COMPLETED
    assert rebuilt.status == IndexStatus.COMPLETED
    assert rebuilt.progress == 100
    assert rebuilt.indexed_chunks == 1
    assert db_session.scalar(select(func.count(EmbeddingRecord.id))) == 1
    assert db_session.scalar(select(func.count(DocumentIndexJob.id))) == 2


def test_semantic_hybrid_metadata_filter_and_delete(db_session: Session) -> None:
    provider = DeterministicEmbeddingProvider()
    store = PgVectorStore(db_session)
    first = record(provider)
    second = replace(
        record(
            provider,
            chunk_id="chunk-2",
            document_id="document-2",
            article="Điều 9",
            content="Điều 9. Cơ quan chủ trì có trách nhiệm báo cáo hằng quý.",
        ),
        workspace_id="workspace-2",
    )
    assert store.upsert_chunks([first, second]) == 2

    query_vector = provider.embed_query(first.content, model_alias="Vietnamese_Embedding")
    semantic = store.similarity_search(
        query_vector,
        filters=VectorMetadataFilter(workspace_id="workspace-1", article="Điều 3"),
        limit=20,
    )
    hybrid = store.hybrid_search(
        query_vector,
        "thời hạn 30 ngày",
        filters=VectorMetadataFilter(document_ids=("document-1",)),
        limit=20,
    )

    assert [item.chunk_id for item in semantic] == ["chunk-1"]
    assert hybrid[0].chunk_id == "chunk-1"
    assert hybrid[0].keyword_score > 0
    assert store.delete_document("document-1") == 1
    assert (
        store.similarity_search(
            query_vector,
            filters=VectorMetadataFilter(document_ids=("document-1",)),
            limit=20,
        )
        == []
    )


def test_retrieval_uses_top_20_or_top_40(db_session: Session) -> None:
    provider = DeterministicEmbeddingProvider()
    store = PgVectorStore(db_session)
    store.upsert_chunks([record(provider)])
    retrieval = HybridRetrievalService(vector_store=store, embedding_provider=provider)

    one_document = retrieval.retrieve(
        "thời hạn phê duyệt",
        filters=RetrievalFilters(workspace_id="workspace-1", document_ids=["document-1"]),
    )
    multiple_documents = retrieval.retrieve(
        "thời hạn phê duyệt",
        filters=RetrievalFilters(
            workspace_id="workspace-1",
            document_ids=["document-1", "document-2"],
        ),
    )

    assert one_document[0].chunk_id == "chunk-1"
    assert multiple_documents[0].chunk_id == "chunk-1"

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sqlalchemy.orm import Session

from app.chat.qa_pipeline import QuestionAnsweringPipeline
from app.chat.schemas import AnswerSchema, AnswerStatus, ChatQuestionRequest, ChatSessionCreate
from app.chat.service import ChatService
from app.reranking.adapters.mock.provider import FailingRerankerProvider, LexicalRerankerProvider
from app.reranking.service import RerankingService
from app.retrieval.service import HybridRetrievalService
from app.streaming.sse import answer_event_stream
from app.vector_store.adapters.mock.embedding import DeterministicEmbeddingProvider
from app.vector_store.contracts import VectorSearchHit
from app.vector_store.pgvector_store import PgVectorStore

from .test_vector_retrieval import record


class RecordingModelRouter:
    def __init__(self) -> None:
        self.aliases: list[str] = []

    def generate(
        self,
        *,
        model_alias: str,
        prompt: str,
        context: list[dict[str, Any]],
        private: bool,
    ) -> str:
        del prompt, private
        self.aliases.append(model_alias)
        return f"Theo nguồn: {context[0]['content']}"


def hit(chunk_id: str = "chunk-1", score: float = 0.9) -> VectorSearchHit:
    return VectorSearchHit(
        record_id=f"record-{chunk_id}",
        chunk_id=chunk_id,
        document_id="document-1",
        workspace_id="workspace-1",
        content="Thời hạn phê duyệt quyết toán là 30 ngày.",
        normalized_content="thời hạn phê duyệt quyết toán là 30 ngày",
        score=score,
        semantic_score=score,
        keyword_score=score,
        language="vi",
        chapter="Chương I",
        article="Điều 3",
        clause="Khoản 2",
        point=None,
        pdf_page_start=13,
        pdf_page_end=13,
        printed_page_start=14,
        printed_page_end=14,
        entity_metadata={"boundingBoxes": [{"pageIndex": 13, "x1": 10, "y1": 20}]},
        embedding_model="Vietnamese_Embedding",
        embedding_version="1",
    )


def pipeline(db_session: Session, router: RecordingModelRouter) -> QuestionAnsweringPipeline:
    return QuestionAnsweringPipeline(
        retrieval=HybridRetrievalService(
            vector_store=PgVectorStore(db_session),
            embedding_provider=DeterministicEmbeddingProvider(),
        ),
        reranking=RerankingService(LexicalRerankerProvider()),
        model_router=router,
    )


def test_reranking_and_fallback() -> None:
    candidates = [hit("lower", 0.2), hit("higher", 0.9)]
    normal = RerankingService(LexicalRerankerProvider()).rerank(
        "thời hạn 30 ngày", candidates, comprehensive=False
    )
    fallback = RerankingService(FailingRerankerProvider()).rerank(
        "thời hạn", candidates, comprehensive=False
    )

    assert normal.available is True
    assert fallback.items[0].hit.chunk_id == "higher"
    assert fallback.warnings == ["RERANKING_UNAVAILABLE"]
    assert fallback.confidence_multiplier == 0.7


def test_qa_with_citation_and_chat_history(db_session: Session) -> None:
    provider = DeterministicEmbeddingProvider()
    PgVectorStore(db_session).upsert_chunks([record(provider)])
    router = RecordingModelRouter()
    service = ChatService(db_session, qa_pipeline=pipeline(db_session, router))
    chat_session = service.create_session("workspace-1", ChatSessionCreate())

    exchange = service.ask(
        chat_session.id,
        ChatQuestionRequest(
            question="Điều 3 thời hạn phê duyệt quyết toán là 30 ngày",
            document_ids=["document-1"],
        ),
    )
    history = service.list_messages(chat_session.id)

    assert exchange.answer.answer_status == AnswerStatus.SUPPORTED
    assert exchange.answer.citations[0].pdf_page_index == 13
    assert len(history) == 2
    assert router.aliases == ["DeepSeek-V4-Flash"]


def test_qa_not_found(db_session: Session) -> None:
    answer = pipeline(db_session, RecordingModelRouter()).answer(
        "Không có nội dung này",
        workspace_id="workspace-1",
        document_ids=["document-1"],
        private=False,
    )

    assert answer.answer_status == AnswerStatus.NOT_FOUND
    assert answer.citations == []


def test_multi_document_conflict_and_generator_selection(db_session: Session) -> None:
    provider = DeterministicEmbeddingProvider()
    first = record(provider)
    second = replace(
        record(
            provider,
            chunk_id="chunk-2",
            document_id="document-2",
            content="Điều 3. Thời hạn phê duyệt quyết toán là 45 ngày.",
        ),
        article="Điều 3",
    )
    PgVectorStore(db_session).upsert_chunks([first, second])
    router = RecordingModelRouter()

    answer = pipeline(db_session, router).answer(
        "Thời hạn phê duyệt quyết toán là bao nhiêu ngày?",
        workspace_id="workspace-1",
        document_ids=["document-1", "document-2"],
        private=False,
    )

    assert answer.answer_status == AnswerStatus.CONFLICTING
    assert answer.conflicts
    assert {citation.document_id for citation in answer.citations} == {
        "document-1",
        "document-2",
    }
    assert router.aliases == ["GLM-5.2"]


def test_streaming_emits_metadata_tokens_citations_and_done() -> None:
    answer = AnswerSchema(
        answer="Thời hạn là 30 ngày theo Điều 3.",
        answer_status=AnswerStatus.SUPPORTED,
        confidence=0.9,
    )
    events = "".join(answer_event_stream(answer))

    assert "event: metadata" in events
    assert "event: token" in events
    assert "event: done" in events

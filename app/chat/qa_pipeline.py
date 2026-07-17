from __future__ import annotations

from dataclasses import dataclass

from app.chat.citations import ChunkCitationResolver
from app.chat.model_router import ModelRouter
from app.chat.schemas import AnswerSchema, AnswerStatus
from app.chat.source_validation import SourceValidator
from app.reranking.service import RerankingService
from app.retrieval.schemas import RetrievalFilters
from app.retrieval.service import HybridRetrievalService
from app.vector_store.contracts import VectorSearchHit


@dataclass(frozen=True, slots=True)
class QuestionIntent:
    name: str
    comprehensive: bool


class QuestionAnsweringPipeline:
    def __init__(
        self,
        *,
        retrieval: HybridRetrievalService,
        reranking: RerankingService,
        model_router: ModelRouter,
        citation_resolver: ChunkCitationResolver | None = None,
        source_validator: SourceValidator | None = None,
    ) -> None:
        self.retrieval = retrieval
        self.reranking = reranking
        self.model_router = model_router
        self.citation_resolver = citation_resolver or ChunkCitationResolver()
        self.source_validator = source_validator or SourceValidator()

    def answer(
        self,
        question: str,
        *,
        workspace_id: str,
        document_ids: list[str],
        private: bool,
    ) -> AnswerSchema:
        intent = self._classify_intent(question, document_ids)
        queries = self._build_queries(question, intent)
        candidates: dict[str, VectorSearchHit] = {}
        filters = RetrievalFilters(workspace_id=workspace_id, document_ids=document_ids)
        for query in queries:
            for hit in self.retrieval.retrieve(query, filters=filters):
                previous = candidates.get(hit.chunk_id)
                if previous is None or hit.score > previous.score:
                    candidates[hit.chunk_id] = hit
        limit = 40 if len(document_ids) > 1 else 20
        retrieved = sorted(candidates.values(), key=lambda item: item.score, reverse=True)[:limit]
        if not retrieved:
            return AnswerSchema(
                answer="Không tìm thấy thông tin phù hợp trong các tài liệu đã chọn.",
                answer_status=AnswerStatus.NOT_FOUND,
                confidence=0,
                limitations=["Không có nguồn phù hợp để tạo câu trả lời."],
            )

        reranked = self.reranking.rerank(
            question,
            retrieved,
            comprehensive=intent.comprehensive,
        )
        context = [
            {
                "chunkId": item.hit.chunk_id,
                "documentId": item.hit.document_id,
                "content": item.hit.content,
                "article": item.hit.article,
                "clause": item.hit.clause,
            }
            for item in reranked.items
        ]
        model_alias = self._generator_alias(document_ids, private)
        warnings = list(reranked.warnings)
        try:
            generated = self.model_router.generate(
                model_alias=model_alias,
                prompt=question,
                context=context,
                private=private,
            )
        except Exception:
            generated = self._generate_with_fallback(question, context, private)
            warnings.append("MODEL_FALLBACK")

        citations = self.citation_resolver.resolve(reranked.items)
        citations = self.citation_resolver.validate(citations, reranked.items)
        conflicts = self.source_validator.detect_conflicts(question, reranked.items)
        confidence = self._confidence(reranked.items) * reranked.confidence_multiplier
        if not reranked.available:
            confidence = min(confidence, 0.69)
        if not citations:
            status = AnswerStatus.LOW_CONFIDENCE_SOURCE
            confidence = min(confidence, 0.35)
        elif conflicts:
            status = AnswerStatus.CONFLICTING
        elif confidence < 0.5:
            status = AnswerStatus.LOW_CONFIDENCE_SOURCE
        elif reranked.available:
            status = AnswerStatus.SUPPORTED
        else:
            status = AnswerStatus.PARTIALLY_SUPPORTED
        limitations = []
        if not reranked.available:
            limitations.append("Reranker không khả dụng; thứ tự nguồn dùng vector score.")
        return AnswerSchema(
            answer=generated,
            answer_status=status,
            confidence=round(confidence, 4),
            citations=citations,
            conflicts=conflicts,
            limitations=limitations,
            warnings=warnings,
        )

    @staticmethod
    def _classify_intent(question: str, document_ids: list[str]) -> QuestionIntent:
        lowered = question.casefold()
        comprehensive_markers = (
            "so sánh",
            "tổng hợp",
            "ngân sách",
            "kinh phí",
            "deadline",
            "thời hạn",
            "trách nhiệm",
            "pháp lý",
            "số liệu",
        )
        comprehensive = len(document_ids) > 1 or any(
            marker in lowered for marker in comprehensive_markers
        )
        return QuestionIntent(
            name="COMPREHENSIVE" if comprehensive else "FACTUAL", comprehensive=comprehensive
        )

    @staticmethod
    def _build_queries(question: str, intent: QuestionIntent) -> list[str]:
        queries = [question]
        lowered = question.casefold()
        if "thời hạn" in lowered or "deadline" in lowered:
            queries.append(f"{question} số ngày thời điểm bắt đầu kết thúc")
        if "kinh phí" in lowered or "ngân sách" in lowered:
            queries.append(f"{question} tổng mức vốn nguồn vốn đơn vị tiền")
        if intent.comprehensive:
            queries.append(f"quy định trách nhiệm và căn cứ liên quan {question}")
        return queries[:3]

    @staticmethod
    def _generator_alias(document_ids: list[str], private: bool) -> str:
        if private:
            return "gpt-oss-120b"
        return "GLM-5.2" if len(document_ids) > 1 else "DeepSeek-V4-Flash"

    def _generate_with_fallback(
        self,
        question: str,
        context: list[dict],
        private: bool,
    ) -> str:
        last_error: Exception | None = None
        for alias in ("GLM-5.1", "Qwen3.6-27B"):
            try:
                return self.model_router.generate(
                    model_alias=alias,
                    prompt=question,
                    context=context,
                    private=private,
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError("No generator model is available") from last_error

    @staticmethod
    def _confidence(items) -> float:
        if not items:
            return 0
        scores = [item.rerank_score for item in items[:5]]
        return max(0.0, min(1.0, sum(scores) / len(scores)))

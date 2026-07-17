from app.reranking.contracts import RerankedHit, RerankOutcome
from app.reranking.provider import RERANKER_MODEL, RerankerProvider
from app.vector_store.contracts import VectorSearchHit


class RerankingService:
    def __init__(self, provider: RerankerProvider) -> None:
        self.provider = provider

    def rerank(
        self,
        question: str,
        candidates: list[VectorSearchHit],
        *,
        comprehensive: bool,
    ) -> RerankOutcome:
        keep = 15 if comprehensive else 8
        try:
            scores = self.provider.score(
                question,
                [candidate.content for candidate in candidates],
                model_alias=RERANKER_MODEL,
            )
            if len(scores) != len(candidates):
                raise RuntimeError("reranker returned an invalid score count")
            ranked = sorted(
                (
                    RerankedHit(hit=candidate, rerank_score=max(0.0, min(1.0, score)))
                    for candidate, score in zip(candidates, scores, strict=True)
                ),
                key=lambda item: item.rerank_score,
                reverse=True,
            )[:keep]
            return RerankOutcome(
                items=ranked,
                warnings=[],
                confidence_multiplier=1,
                available=True,
            )
        except Exception:
            fallback = [
                RerankedHit(hit=candidate, rerank_score=candidate.score)
                for candidate in sorted(candidates, key=lambda item: item.score, reverse=True)[
                    :keep
                ]
            ]
            return RerankOutcome(
                items=fallback,
                warnings=["RERANKING_UNAVAILABLE"],
                confidence_multiplier=0.7,
                available=False,
            )

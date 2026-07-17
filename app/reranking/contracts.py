from dataclasses import dataclass

from app.vector_store.contracts import VectorSearchHit


@dataclass(frozen=True, slots=True)
class RerankedHit:
    hit: VectorSearchHit
    rerank_score: float


@dataclass(frozen=True, slots=True)
class RerankOutcome:
    items: list[RerankedHit]
    warnings: list[str]
    confidence_multiplier: float
    available: bool

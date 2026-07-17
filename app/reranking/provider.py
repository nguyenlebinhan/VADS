from typing import Protocol


class RerankerProvider(Protocol):
    def score(
        self,
        query: str,
        documents: list[str],
        *,
        model_alias: str,
    ) -> list[float]: ...

    def health_check(self) -> bool: ...


RERANKER_MODEL = "bge-reranker-v2-m3"

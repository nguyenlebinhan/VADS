from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str], *, model_alias: str) -> list[list[float]]: ...

    def embed_query(self, text: str, *, model_alias: str) -> list[float]: ...

    def version(self, model_alias: str) -> str: ...

    def health_check(self) -> bool: ...


VIETNAMESE_EMBEDDING_MODEL = "Vietnamese_Embedding"
MULTILINGUAL_EMBEDDING_MODEL = "multilingual-e5-large"

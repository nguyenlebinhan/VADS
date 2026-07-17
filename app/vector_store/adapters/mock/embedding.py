import hashlib
import math
import re

from app.vector_store.models import EMBEDDING_DIMENSION


class DeterministicEmbeddingProvider:
    """Test/local adapter; production must inject the model gateway implementation."""

    def embed_documents(self, texts: list[str], *, model_alias: str) -> list[list[float]]:
        return [self._embed(text, model_alias) for text in texts]

    def embed_query(self, text: str, *, model_alias: str) -> list[float]:
        return self._embed(text, model_alias)

    def version(self, model_alias: str) -> str:
        del model_alias
        return "mock-hash-v1"

    def health_check(self) -> bool:
        return True

    @staticmethod
    def _embed(text: str, model_alias: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSION
        tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        for token in tokens:
            digest = hashlib.sha256(f"{model_alias}:{token}".encode()).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSION
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

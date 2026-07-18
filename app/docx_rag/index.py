from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from app.docx_rag.schemas import DocxChunk, SearchResult

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.casefold())


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


class DocxRagIndex:
    def __init__(
        self,
        chunks: list[DocxChunk],
        *,
        embeddings: list[list[float]] | None = None,
        source_signature: str = "",
        embedding_model: str | None = None,
        embedding_error: str | None = None,
    ) -> None:
        if embeddings is not None and len(embeddings) != len(chunks):
            raise ValueError("Each chunk must have exactly one embedding")
        self.chunks = chunks
        self.embeddings = embeddings
        self.source_signature = source_signature
        self.embedding_model = embedding_model
        self.embedding_error = embedding_error

    @property
    def has_embeddings(self) -> bool:
        return bool(self.embeddings) and len(self.embeddings or []) == len(self.chunks)

    def search_by_embedding(
        self, query_embedding: list[float], *, top_k: int
    ) -> list[SearchResult]:
        if not self.has_embeddings:
            return []
        scored = [
            SearchResult(chunk=chunk, score=_cosine(query_embedding, embedding))
            for chunk, embedding in zip(self.chunks, self.embeddings or [], strict=True)
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def search_lexical(self, query: str, *, top_k: int) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        tokenized_chunks = [tokenize(chunk.text) for chunk in self.chunks]
        document_count = max(len(tokenized_chunks), 1)
        document_frequency = Counter(
            token for tokens in tokenized_chunks for token in set(tokens)
        )

        def idf(token: str) -> float:
            return math.log((1 + document_count) / (1 + document_frequency[token])) + 1.0

        query_counts = Counter(query_tokens)
        query_weights = {token: count * idf(token) for token, count in query_counts.items()}
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
        normalized_query = " ".join(query_tokens)
        results: list[SearchResult] = []

        for chunk, tokens in zip(self.chunks, tokenized_chunks, strict=True):
            counts = Counter(tokens)
            chunk_weights = {token: counts[token] * idf(token) for token in query_weights}
            chunk_norm = math.sqrt(sum(weight * weight for weight in chunk_weights.values()))
            dot = sum(query_weights[token] * chunk_weights[token] for token in query_weights)
            score = dot / (query_norm * chunk_norm) if query_norm and chunk_norm else 0.0
            if normalized_query and normalized_query in " ".join(tokens):
                score += 0.15
            results.append(SearchResult(chunk=chunk, score=score))

        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "source_signature": self.source_signature,
            "embedding_model": self.embedding_model,
            "embedding_error": self.embedding_error,
            "chunks": [chunk.model_dump(mode="json") for chunk in self.chunks],
            "embeddings": self.embeddings,
        }
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary_path.replace(path)

    @classmethod
    def load(cls, path: Path) -> DocxRagIndex:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != 1:
            raise ValueError("Unsupported DOCX RAG index version")
        return cls(
            [DocxChunk.model_validate(item) for item in payload["chunks"]],
            embeddings=payload.get("embeddings"),
            source_signature=payload.get("source_signature", ""),
            embedding_model=payload.get("embedding_model"),
            embedding_error=payload.get("embedding_error"),
        )

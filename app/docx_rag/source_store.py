from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Protocol

from app.docx_rag.schemas import SourceCitation

DEFAULT_QUERY_TTL_SECONDS = 30 * 60
QUERY_TTL_ENV_VAR = "VADS_DOCX_RAG_QUERY_TTL_SECONDS"


@dataclass(frozen=True, slots=True)
class StoredSourceResult:
    sources: list[SourceCitation]
    page_note: str


class SourceStore(Protocol):
    def save(
        self,
        query_id: str,
        sources: Sequence[SourceCitation],
        page_note: str,
    ) -> None: ...

    def get(self, query_id: str) -> StoredSourceResult | None: ...

    def delete(self, query_id: str) -> None: ...

    def cleanup_expired(self) -> int: ...


@dataclass(slots=True)
class _StoreEntry:
    result: StoredSourceResult
    expires_at: float


class InMemorySourceStore:
    """Thread-safe, process-local source storage with per-query expiration."""

    def __init__(
        self,
        ttl_seconds: float | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.ttl_seconds = (
            self._configured_ttl_seconds() if ttl_seconds is None else float(ttl_seconds)
        )
        if self.ttl_seconds <= 0:
            raise ValueError("DOCX RAG query TTL must be greater than zero")
        self._clock = clock
        self._entries: dict[str, _StoreEntry] = {}
        self._lock = RLock()

    @staticmethod
    def _configured_ttl_seconds() -> float:
        configured = os.getenv(QUERY_TTL_ENV_VAR)
        if configured is None or not configured.strip():
            return float(DEFAULT_QUERY_TTL_SECONDS)
        try:
            return float(configured)
        except ValueError as error:
            raise ValueError(f"{QUERY_TTL_ENV_VAR} must be a number") from error

    @staticmethod
    def _copy_result(result: StoredSourceResult) -> StoredSourceResult:
        return StoredSourceResult(
            sources=[source.model_copy(deep=True) for source in result.sources],
            page_note=result.page_note,
        )

    def _cleanup_expired_locked(self, now: float) -> int:
        expired_ids = [
            query_id
            for query_id, entry in self._entries.items()
            if entry.expires_at <= now
        ]
        for query_id in expired_ids:
            del self._entries[query_id]
        return len(expired_ids)

    def save(
        self,
        query_id: str,
        sources: Sequence[SourceCitation],
        page_note: str,
    ) -> None:
        result = StoredSourceResult(
            sources=[source.model_copy(deep=True) for source in sources],
            page_note=page_note,
        )
        with self._lock:
            now = self._clock()
            self._cleanup_expired_locked(now)
            self._entries[query_id] = _StoreEntry(
                result=result,
                expires_at=now + self.ttl_seconds,
            )

    def get(self, query_id: str) -> StoredSourceResult | None:
        with self._lock:
            entry = self._entries.get(query_id)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._entries[query_id]
                return None
            return self._copy_result(entry.result)

    def delete(self, query_id: str) -> None:
        with self._lock:
            self._entries.pop(query_id, None)

    def cleanup_expired(self) -> int:
        with self._lock:
            return self._cleanup_expired_locked(self._clock())

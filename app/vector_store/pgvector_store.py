from __future__ import annotations

import math
import re
from dataclasses import replace

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.vector_store.contracts import (
    EmbeddingRecordInput,
    VectorMetadataFilter,
    VectorSearchHit,
)
from app.vector_store.models import EmbeddingRecord


class PgVectorStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_chunks(self, records: list[EmbeddingRecordInput]) -> int:
        for record in records:
            existing = self.session.scalar(
                select(EmbeddingRecord).where(
                    EmbeddingRecord.chunk_id == record.chunk_id,
                    EmbeddingRecord.embedding_model == record.embedding_model,
                    EmbeddingRecord.embedding_version == record.embedding_version,
                )
            )
            values = self._record_values(record)
            if existing is None:
                self.session.add(EmbeddingRecord(**values))
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
        self.session.commit()
        return len(records)

    def delete_document(self, document_id: str) -> int:
        result = self.session.execute(
            delete(EmbeddingRecord).where(EmbeddingRecord.document_id == document_id)
        )
        self.session.commit()
        return int(result.rowcount or 0)

    def similarity_search(
        self,
        query_vector: list[float],
        *,
        filters: VectorMetadataFilter,
        limit: int,
    ) -> list[VectorSearchHit]:
        statement = self._filtered_statement(filters)
        dialect = self.session.get_bind().dialect.name
        if dialect == "postgresql":
            distance = EmbeddingRecord.vector.cosine_distance(query_vector)
            rows = self.session.execute(
                statement.add_columns(distance.label("distance")).order_by(distance).limit(limit)
            ).all()
            return [
                self._hit(record, semantic=max(0.0, 1.0 - float(distance_value)))
                for record, distance_value in rows
            ]

        records = list(self.session.scalars(statement))
        ranked = sorted(
            ((record, self._cosine(query_vector, list(record.vector))) for record in records),
            key=lambda item: item[1],
            reverse=True,
        )[:limit]
        return [self._hit(record, semantic=max(0.0, score)) for record, score in ranked]

    def hybrid_search(
        self,
        query_vector: list[float],
        query_text: str,
        *,
        filters: VectorMetadataFilter,
        limit: int,
    ) -> list[VectorSearchHit]:
        candidates = self.similarity_search(
            query_vector,
            filters=filters,
            limit=max(limit * 3, 40),
        )
        query_terms = self._terms(query_text)
        reranked: list[VectorSearchHit] = []
        for hit in candidates:
            keyword_score = self._keyword_score(query_terms, self._terms(hit.normalized_content))
            combined = (0.7 * hit.semantic_score) + (0.3 * keyword_score)
            reranked.append(replace(hit, score=combined, keyword_score=keyword_score))
        return sorted(reranked, key=lambda item: item.score, reverse=True)[:limit]

    def health_check(self) -> bool:
        try:
            self.session.execute(text("SELECT 1"))
        except Exception:
            self.session.rollback()
            return False
        return True

    def _filtered_statement(self, filters: VectorMetadataFilter):
        statement = select(EmbeddingRecord)
        if filters.workspace_id:
            statement = statement.where(EmbeddingRecord.workspace_id == filters.workspace_id)
        if filters.document_ids:
            statement = statement.where(EmbeddingRecord.document_id.in_(filters.document_ids))
        for field in ("chapter", "article", "clause", "point", "node_type", "agency", "language"):
            value = getattr(filters, field)
            if value:
                statement = statement.where(getattr(EmbeddingRecord, field) == value)
        if filters.issued_date:
            statement = statement.where(EmbeddingRecord.issued_date == filters.issued_date)
        return statement

    @staticmethod
    def _record_values(record: EmbeddingRecordInput) -> dict:
        return {
            field: getattr(record, field) for field in EmbeddingRecordInput.__dataclass_fields__
        }

    @staticmethod
    def _hit(record: EmbeddingRecord, *, semantic: float) -> VectorSearchHit:
        return VectorSearchHit(
            record_id=record.id,
            chunk_id=record.chunk_id,
            document_id=record.document_id,
            workspace_id=record.workspace_id,
            content=record.content,
            normalized_content=record.normalized_content,
            score=semantic,
            semantic_score=semantic,
            keyword_score=0,
            language=record.language,
            chapter=record.chapter,
            article=record.article,
            clause=record.clause,
            point=record.point,
            pdf_page_start=record.pdf_page_start,
            pdf_page_end=record.pdf_page_end,
            printed_page_start=record.printed_page_start,
            printed_page_end=record.printed_page_end,
            entity_metadata=record.entity_metadata,
            embedding_model=record.embedding_model,
            embedding_version=record.embedding_version,
        )

    @staticmethod
    def _cosine(first: list[float], second: list[float]) -> float:
        denominator = math.sqrt(sum(x * x for x in first)) * math.sqrt(sum(x * x for x in second))
        return sum(x * y for x, y in zip(first, second, strict=False)) / (denominator or 1)

    @staticmethod
    def _terms(value: str) -> set[str]:
        return set(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))

    @staticmethod
    def _keyword_score(query: set[str], content: set[str]) -> float:
        return len(query & content) / (len(query) or 1)

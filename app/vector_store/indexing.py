from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.documents.interfaces import DocumentChunkReader
from app.exceptions import NotFoundError
from app.vector_store.adapters.document_context import DocumentContextReader
from app.vector_store.contracts import EmbeddingRecordInput
from app.vector_store.embedding import (
    MULTILINGUAL_EMBEDDING_MODEL,
    VIETNAMESE_EMBEDDING_MODEL,
    EmbeddingProvider,
)
from app.vector_store.interfaces import VectorStore
from app.vector_store.models import (
    EMBEDDING_DIMENSION,
    DocumentIndexJob,
    IndexStatus,
)
from app.vector_store.schemas import IndexStatusData


class DocumentIndexingService:
    def __init__(
        self,
        session: Session,
        *,
        chunk_reader: DocumentChunkReader,
        context_reader: DocumentContextReader,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.session = session
        self.chunk_reader = chunk_reader
        self.context_reader = context_reader
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def index_document(self, document_id: str, *, rebuild: bool = False) -> IndexStatusData:
        context = self.context_reader.get_context(document_id)
        if context is None:
            raise NotFoundError("DOCUMENT", document_id)
        if rebuild:
            self.vector_store.delete_document(document_id)

        attempt = (
            self.session.scalar(
                select(func.max(DocumentIndexJob.attempt)).where(
                    DocumentIndexJob.document_id == document_id
                )
            )
            or 0
        ) + 1
        job = DocumentIndexJob(
            document_id=document_id,
            workspace_id=context.workspace_id,
            attempt=attempt,
            status=IndexStatus.INDEXING,
            started_at=datetime.now(UTC),
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)

        try:
            chunks = self.chunk_reader.list_chunks(document_id)
            job.total_chunks = len(chunks)
            grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
            languages: list[str] = []
            for index, chunk in enumerate(chunks):
                language = self._detect_language(chunk.content)
                languages.append(language)
                model_alias = (
                    VIETNAMESE_EMBEDDING_MODEL if language == "vi" else MULTILINGUAL_EMBEDDING_MODEL
                )
                grouped[model_alias].append((index, chunk.content))

            vectors: dict[int, tuple[list[float], str]] = {}
            for model_alias, items in grouped.items():
                embedded = self.embedding_provider.embed_documents(
                    [content for _, content in items], model_alias=model_alias
                )
                if len(embedded) != len(items):
                    raise RuntimeError("Embedding provider returned an invalid batch length")
                for (chunk_index, _), vector in zip(items, embedded, strict=True):
                    if len(vector) != EMBEDDING_DIMENSION:
                        raise RuntimeError(
                            "Embedding vector dimension does not match pgvector schema"
                        )
                    vectors[chunk_index] = (vector, model_alias)

            records: list[EmbeddingRecordInput] = []
            for index, chunk in enumerate(chunks):
                vector, model_alias = vectors[index]
                records.append(
                    EmbeddingRecordInput(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        workspace_id=context.workspace_id,
                        vector=vector,
                        content=chunk.content,
                        normalized_content=chunk.normalized_content,
                        language=languages[index],
                        chapter=chunk.chapter,
                        article=chunk.article,
                        clause=chunk.clause,
                        point=chunk.point,
                        pdf_page_start=chunk.pdf_page_start,
                        pdf_page_end=chunk.pdf_page_end,
                        printed_page_start=chunk.printed_page_start,
                        printed_page_end=chunk.printed_page_end,
                        entity_metadata={
                            "sectionId": chunk.section_id,
                            "appendix": chunk.appendix,
                            "formCode": chunk.form_code,
                            "boundingBoxes": chunk.bounding_boxes,
                        },
                        embedding_model=model_alias,
                        embedding_version=self.embedding_provider.version(model_alias),
                    )
                )
            indexed = self.vector_store.upsert_chunks(records)
            job.status = IndexStatus.COMPLETED
            job.indexed_chunks = indexed
            job.progress = 100
            job.embedding_models = sorted(grouped)
            job.completed_at = datetime.now(UTC)
            self.session.commit()
            self.session.refresh(job)
            return self._status(job)
        except Exception as exc:
            self.session.rollback()
            failed = self.session.get(DocumentIndexJob, job.id)
            if failed is not None:
                failed.status = IndexStatus.FAILED
                failed.error_code = "DOCUMENT_INDEXING_FAILED"
                failed.error_message = str(exc)[:4000]
                failed.completed_at = datetime.now(UTC)
                self.session.commit()
            raise

    def get_status(self, document_id: str) -> IndexStatusData:
        job = self.session.scalar(
            select(DocumentIndexJob)
            .where(DocumentIndexJob.document_id == document_id)
            .order_by(DocumentIndexJob.attempt.desc())
            .limit(1)
        )
        if job is None:
            raise NotFoundError("DOCUMENT_INDEX_JOB", document_id)
        return self._status(job)

    @staticmethod
    def _detect_language(content: str) -> str:
        lowered = content.casefold()
        if re.search(r"[ăâđêôơưà-ỹ]", lowered) or re.search(
            r"\b(điều|khoản|ngày|cơ quan|trách nhiệm|thời hạn)\b", lowered
        ):
            return "vi"
        return "multilingual"

    @staticmethod
    def _status(job: DocumentIndexJob) -> IndexStatusData:
        return IndexStatusData(
            job_id=job.id,
            document_id=job.document_id,
            workspace_id=job.workspace_id,
            status=job.status,
            progress=job.progress,
            total_chunks=job.total_chunks,
            indexed_chunks=job.indexed_chunks,
            embedding_models=job.embedding_models,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            updated_at=job.updated_at,
        )

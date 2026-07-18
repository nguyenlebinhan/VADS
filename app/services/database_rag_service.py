from __future__ import annotations

import re

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.docx_rag.embeddings import OpenAIAPIClient
from app.docx_rag.index import DocxRagIndex, tokenize
from app.docx_rag.schemas import (
    DocxChunk,
    OpenAIConfigurationError,
    OpenAIRequestError,
    SearchResult,
)
from app.exceptions import AppError, ConflictError, NotFoundError
from app.model.chunking import DocumentChunk
from app.model.documents import Document
from app.model.security import DocumentGrantPermission, DocumentPermission
from app.model.users import User
from app.policies.document_policy import DocumentPolicy
from app.schemas.rag import RagQueryRequest, RagQueryResponse, RagSourcePublic

SOURCE_MARKER_RE = re.compile(r"\[(?:Nguon|Nguồn|Source)\s+(\d+)]", re.IGNORECASE)


class DatabaseRagService:
    def __init__(self, session: Session, *, client: OpenAIAPIClient | None = None) -> None:
        self.session = session
        self.client = client

    def answer(self, *, actor: User, payload: RagQueryRequest) -> RagQueryResponse:
        documents = self._visible_documents(actor, payload.document_ids)
        rows = self.session.execute(
            select(DocumentChunk, Document.display_name)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.document_id.in_(documents))
            .order_by(DocumentChunk.document_id, DocumentChunk.order_index)
        ).all()
        if not rows:
            raise ConflictError(
                "DOCUMENT_NOT_READY_FOR_RAG",
                "Tai lieu chua xu ly xong hoac chua co chunk trong database.",
            )

        document_titles = {document.id: document.display_name for document in documents.values()}
        chunks = [
            DocxChunk(
                chunk_id=chunk.id,
                file_name=title,
                text=chunk.content,
                article=chunk.article,
                clause=chunk.clause,
                page_number=chunk.pdf_page_start + 1,
            )
            for chunk, title in rows
        ]
        results = DocxRagIndex(chunks).search_lexical(
            payload.question,
            top_k=payload.top_k,
        )
        if not results:
            raise ConflictError(
                "RAG_CONTEXT_NOT_FOUND",
                "Khong tim thay noi dung phu hop trong cac tai lieu da chon.",
            )

        chunk_document_ids = {chunk.id: chunk.document_id for chunk, _ in rows}
        context = self._format_context(results, chunk_document_ids)
        try:
            answer = (self.client or OpenAIAPIClient()).answer_with_context(
                question=payload.question,
                context=context,
            )
        except OpenAIConfigurationError as error:
            raise AppError(
                status_code=503,
                code="RAG_MODEL_NOT_CONFIGURED",
                message="Chua cau hinh API key cho mo hinh RAG.",
            ) from error
        except OpenAIRequestError as error:
            raise AppError(
                status_code=502,
                code="RAG_MODEL_REQUEST_FAILED",
                message="Khong the nhan cau tra loi tu mo hinh RAG.",
            ) from error

        used_numbers = {
            int(match.group(1))
            for match in SOURCE_MARKER_RE.finditer(answer)
            if 1 <= int(match.group(1)) <= len(results)
        }
        selected = [
            result
            for number, result in enumerate(results, start=1)
            if not used_numbers or number in used_numbers
        ]
        return RagQueryResponse(
            answer=answer,
            retrieval_mode="database_lexical",
            sources=[
                RagSourcePublic(
                    document_id=chunk_document_ids[result.chunk.chunk_id],
                    document_title=document_titles[
                        chunk_document_ids[result.chunk.chunk_id]
                    ],
                    chunk_id=result.chunk.chunk_id,
                    page_number=result.chunk.page_number,
                    article=result.chunk.article,
                    clause=result.chunk.clause,
                    quote=self._best_quote(result.chunk.text, payload.question),
                    score=result.score,
                )
                for result in selected
            ],
        )

    def _visible_documents(
        self,
        actor: User,
        document_ids: list[str],
    ) -> dict[str, Document]:
        unique_ids = list(dict.fromkeys(document_ids))
        documents = self.session.scalars(
            select(Document).where(
                Document.id.in_(unique_ids),
                Document.commune_id == actor.commune_id,
                Document.is_deleted.is_(False),
                Document.deleted_at.is_(None),
            )
        ).all()
        by_id = {document.id: document for document in documents}
        for document_id in unique_ids:
            document = by_id.get(document_id)
            if document is None:
                raise NotFoundError("DOCUMENT", document_id)
            explicit_access = False
            if document.owner_id != actor.id:
                explicit_access = bool(
                    self.session.scalar(
                        select(
                            exists().where(
                                DocumentPermission.document_id == document.id,
                                DocumentPermission.commune_id == actor.commune_id,
                                DocumentPermission.user_id == actor.id,
                                DocumentPermission.permission.in_(
                                    [
                                        DocumentGrantPermission.READ,
                                        DocumentGrantPermission.ASK,
                                    ]
                                ),
                            )
                        )
                    )
                )
            if not DocumentPolicy.can_read(
                actor,
                document,
                has_explicit_access=explicit_access,
            ):
                raise NotFoundError("DOCUMENT", document_id)
        return by_id

    @staticmethod
    def _format_context(
        results: list[SearchResult],
        chunk_document_ids: dict[str, str],
    ) -> str:
        sections: list[str] = []
        for number, result in enumerate(results, start=1):
            chunk = result.chunk
            sections.append(
                "\n".join(
                    [
                        f"[Nguon {number}]",
                        f"document_id={chunk_document_ids[chunk.chunk_id]}",
                        f"document_title={chunk.file_name}",
                        f"chunk_id={chunk.chunk_id}",
                        f"page_number={chunk.page_number}",
                        f"article={chunk.article}",
                        f"clause={chunk.clause}",
                        "text:",
                        chunk.text,
                    ]
                )
            )
        return "\n\n".join(sections)

    @staticmethod
    def _best_quote(text: str, question: str, *, max_chars: int = 600) -> str:
        segments = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text)]
        segments = [segment for segment in segments if segment]
        if not segments:
            return text[:max_chars]
        query_tokens = set(tokenize(question))
        best = max(
            segments,
            key=lambda segment: len(query_tokens.intersection(tokenize(segment))),
        )
        return best[:max_chars].strip()

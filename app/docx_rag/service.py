from __future__ import annotations

import re
from pathlib import Path
from threading import RLock

from app.docx_rag.chunker import chunk_blocks
from app.docx_rag.docx_reader import find_docx_files, read_docx_directory, source_signature
from app.docx_rag.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    OpenAIAPIClient,
    resolve_api_key,
    resolve_config_value,
)
from app.docx_rag.index import DocxRagIndex, tokenize
from app.docx_rag.schemas import (
    DocxRagResult,
    OpenAIRequestError,
    SearchResult,
    SourceCitation,
)

PAGE_NOTE = (
    "page_number is null because DOCX uses a flowing layout and does not store a stable, "
    "device-independent page number."
)
SOURCE_MARKER_RE = re.compile(
    r"\s*\[(?:Nguon|Nguồn|Source)\s+(\d+)\]\s*",
    re.IGNORECASE,
)


class DocxRagService:
    def __init__(
        self,
        data_dir: Path | str | None = None,
        *,
        cache_path: Path | str | None = None,
        client: OpenAIAPIClient | None = None,
    ) -> None:
        self.data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parents[1] / "data"
        )
        repository_root = self.data_dir.resolve().parents[1]
        self.cache_path = (
            Path(cache_path)
            if cache_path is not None
            else repository_root / ".cache" / "docx_rag" / "index.json"
        )
        self.client = client
        self.index: DocxRagIndex | None = None
        self._lock = RLock()

    @property
    def embedding_model(self) -> str:
        if self.client is not None:
            return self.client.embedding_model
        return resolve_config_value("VADS_OPENAI_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL

    def _get_client(self) -> OpenAIAPIClient:
        if self.client is None:
            self.client = OpenAIAPIClient()
        return self.client

    def build_index(
        self,
        *,
        force_rebuild: bool = False,
        use_embeddings: bool = True,
        persist: bool = True,
    ) -> DocxRagIndex:
        with self._lock:
            files = find_docx_files(self.data_dir)
            signature = source_signature(files)
            api_key_available = bool(resolve_api_key(required=False) or self.client is not None)

            if not force_rebuild and self.index is not None:
                if self.index.source_signature == signature:
                    return self.index

            if not force_rebuild and self.cache_path.exists():
                try:
                    cached = DocxRagIndex.load(self.cache_path)
                    cache_matches = (
                        cached.source_signature == signature
                        and cached.embedding_model == self.embedding_model
                    )
                    needs_embeddings = (
                        use_embeddings and api_key_available and not cached.has_embeddings
                    )
                    if cache_matches and not needs_embeddings:
                        self.index = cached
                        return cached
                except (OSError, ValueError, KeyError):
                    pass

            blocks, _ = read_docx_directory(self.data_dir)
            chunks = chunk_blocks(blocks)
            embeddings: list[list[float]] | None = None
            embedding_error: str | None = None

            if use_embeddings:
                try:
                    embeddings = self._get_client().embed_texts([chunk.text for chunk in chunks])
                except Exception as error:  # Retrieval must remain available when embeddings fail.
                    embedding_error = str(error)

            self.index = DocxRagIndex(
                chunks,
                embeddings=embeddings,
                source_signature=signature,
                embedding_model=self.embedding_model,
                embedding_error=embedding_error,
            )
            if persist:
                self.index.save(self.cache_path)
            return self.index

    def search(self, question: str, *, top_k: int = 5) -> tuple[list[SearchResult], str]:
        if not question.strip():
            raise ValueError("Question must not be empty")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        index = self.index or self.build_index()

        if index.has_embeddings:
            try:
                query_embedding = self._get_client().embed_texts([question])[0]
                return index.search_by_embedding(query_embedding, top_k=top_k), "embedding"
            except Exception as error:  # The lexical path is intentionally independent of OpenAI.
                index.embedding_error = str(error)

        return index.search_lexical(question, top_k=top_k), "lexical"

    def answer(
        self,
        question: str,
        *,
        top_k: int = 5,
        force_rebuild: bool = False,
    ) -> DocxRagResult:
        self.build_index(force_rebuild=force_rebuild)
        results, retrieval_mode = self.search(question, top_k=top_k)
        if not results:
            raise OpenAIRequestError("No chunks are available for the question")

        context = self._format_context(results)
        answer = self._get_client().answer_with_context(question=question, context=context)
        used_numbers = {
            int(match.group(1))
            for match in SOURCE_MARKER_RE.finditer(answer)
            if 1 <= int(match.group(1)) <= len(results)
        }
        answer = self._strip_source_markers(answer)
        selected = [
            result
            for number, result in enumerate(results, start=1)
            if not used_numbers or number in used_numbers
        ]
        sources = [self._citation(result, question) for result in selected]
        embedding_error = self.index.embedding_error if self.index is not None else None
        return DocxRagResult(
            answer=answer,
            sources=sources,
            retrieval_mode=retrieval_mode,
            page_note=PAGE_NOTE,
            embedding_error=embedding_error,
        )
    @staticmethod
    def _format_context(results: list[SearchResult]) -> str:
        sections: list[str] = []
        for number, result in enumerate(results, start=1):
            chunk = result.chunk
            sections.append(
                "\n".join(
                    [
                        f"[Nguồn {number}]",
                        f"file={chunk.file_name}",
                        f"chunk_id={chunk.chunk_id}",
                        f"paragraph_indices={chunk.paragraph_indices or None}",
                        f"table_indices={chunk.table_indices or None}",
                        f"article={chunk.article}",
                        f"clause={DocxRagService._display_clause(chunk.clause)}",
                        "text:",
                        chunk.text,
                    ]
                )
            )
        return "\n\n".join(sections)

    @staticmethod
    def _display_clause(value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(
            r"^\s*(?:Khoản|Khoan)\s+",
            "Mục ",
            value,
            count=1,
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _strip_source_markers(answer: str) -> str:
        cleaned = SOURCE_MARKER_RE.sub(" ", answer)
        cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

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

    def _citation(self, result: SearchResult, question: str) -> SourceCitation:
        chunk = result.chunk
        return SourceCitation(
            file_name=chunk.file_name,
            chunk_id=chunk.chunk_id,
            paragraph_index=chunk.paragraph_indices[0] if chunk.paragraph_indices else None,
            table_index=chunk.table_indices[0] if chunk.table_indices else None,
            paragraph_indices=chunk.paragraph_indices,
            table_indices=chunk.table_indices,
            article=chunk.article,
            clause=self._display_clause(chunk.clause),
            page_number=None,
            quote=self._best_quote(chunk.text, question),
            score=result.score,
        )

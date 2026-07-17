from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from typing import Any

from app.citations.schemas import (
    CitationDraft,
    CitationValidationIssue,
    CitationValidationResult,
)
from app.documents.interfaces import DocumentChunkContract, DocumentChunkReader


def normalize_source_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.translate(
        str.maketrans(
            {
                "“": '"',
                "”": '"',
                "‘": "'",
                "’": "'",
                "–": "-",
                "—": "-",
                "\u00a0": " ",
            }
        )
    )
    return " ".join(value.casefold().split())


def _search_form(value: str) -> str:
    normalized = normalize_source_text(value)
    return re.sub(r"[^\w]+", "", normalized, flags=re.UNICODE)


class CitationValidationError(ValueError):
    def __init__(self, result: CitationValidationResult) -> None:
        self.result = result
        detail = "; ".join(f"{issue.code}: {issue.message}" for issue in result.issues)
        super().__init__(detail)


class CitationValidator:
    """Validates source anchors exclusively through the DocumentChunkReader contract."""

    def __init__(
        self,
        chunk_reader: DocumentChunkReader,
        *,
        document_exists: Callable[[str], bool] | None = None,
        bbox_tolerance: float = 1.0,
    ) -> None:
        self.chunk_reader = chunk_reader
        self.document_exists = document_exists
        self.bbox_tolerance = bbox_tolerance

    def validate(
        self,
        citation: CitationDraft,
        *,
        expected_document_id: str | None = None,
    ) -> CitationValidationResult:
        issues: list[CitationValidationIssue] = []
        if expected_document_id is not None and citation.document_id != expected_document_id:
            issues.append(
                self._issue(
                    "CROSS_DOCUMENT_CITATION",
                    "Citation belongs to a different document",
                    "documentId",
                )
            )
        if self.document_exists is not None and not self.document_exists(citation.document_id):
            issues.append(
                self._issue("DOCUMENT_NOT_FOUND", "Citation document does not exist", "documentId")
            )

        chunk: DocumentChunkContract | None = None
        try:
            chunk = self.chunk_reader.get_chunk(citation.chunk_id)
        except (LookupError, KeyError, ValueError):
            issues.append(
                self._issue("CHUNK_NOT_FOUND", "Citation chunk does not exist", "chunkId")
            )
        except Exception as exc:
            if getattr(exc, "code", None) == "CHUNK_NOT_FOUND":
                issues.append(
                    self._issue("CHUNK_NOT_FOUND", "Citation chunk does not exist", "chunkId")
                )
            else:
                raise

        normalized_quote = normalize_source_text(citation.quote)
        if chunk is not None:
            if chunk.document_id != citation.document_id:
                issues.append(
                    self._issue(
                        "CHUNK_DOCUMENT_MISMATCH",
                        "Chunk does not belong to citation document",
                        "chunkId",
                    )
                )
            if not self._quote_exists(citation.quote, chunk):
                issues.append(
                    self._issue(
                        "QUOTE_NOT_FOUND",
                        "Quoted text cannot be mapped to chunk content after normalization",
                        "quote",
                    )
                )
            self._validate_locator("article", citation.article, chunk.article, issues)
            self._validate_locator("clause", citation.clause, chunk.clause, issues)
            self._validate_locator("point", citation.point, chunk.point, issues)
            if not chunk.pdf_page_start <= citation.page <= chunk.pdf_page_end:
                issues.append(
                    self._issue(
                        "PAGE_OUT_OF_RANGE",
                        "Citation page is outside the chunk page range",
                        "page",
                    )
                )
            if citation.bounding_box is not None and not self._bbox_belongs_to_page(
                citation.page,
                citation.bounding_box.model_dump(),
                chunk.bounding_boxes,
            ):
                issues.append(
                    self._issue(
                        "BOUNDING_BOX_PAGE_MISMATCH",
                        "Bounding box is not contained by a chunk anchor on the cited page",
                        "boundingBox",
                    )
                )

        return CitationValidationResult(
            valid=not issues,
            citation=citation,
            normalizedQuote=normalized_quote,
            issues=issues,
        )

    def validate_all(
        self,
        citations: Iterable[CitationDraft],
        *,
        expected_document_id: str | None = None,
    ) -> list[CitationValidationResult]:
        return [
            self.validate(citation, expected_document_id=expected_document_id)
            for citation in citations
        ]

    def validate_or_raise(
        self,
        citation: CitationDraft,
        *,
        expected_document_id: str | None = None,
    ) -> CitationValidationResult:
        result = self.validate(citation, expected_document_id=expected_document_id)
        if not result.valid:
            raise CitationValidationError(result)
        return result

    @staticmethod
    def _quote_exists(quote: str, chunk: DocumentChunkContract) -> bool:
        normalized_quote = normalize_source_text(quote)
        candidates = [chunk.content, chunk.normalized_content]
        if any(normalized_quote in normalize_source_text(candidate) for candidate in candidates):
            return True
        compact_quote = _search_form(quote)
        return bool(compact_quote) and any(
            compact_quote in _search_form(candidate) for candidate in candidates
        )

    @staticmethod
    def _validate_locator(
        field: str,
        cited_value: str | None,
        chunk_value: str | None,
        issues: list[CitationValidationIssue],
    ) -> None:
        if cited_value is None:
            return
        if chunk_value is None or normalize_source_text(cited_value) != normalize_source_text(
            chunk_value
        ):
            issues.append(
                CitationValidator._issue(
                    f"{field.upper()}_MISMATCH",
                    f"Citation {field} does not match chunk metadata",
                    field,
                )
            )

    def _bbox_belongs_to_page(
        self,
        page: int,
        bbox: dict[str, float],
        anchors: list[dict[str, Any]],
    ) -> bool:
        for anchor in anchors:
            page_index = anchor.get("pageIndex", anchor.get("page_index"))
            if page_index != page:
                continue
            anchor_bbox = anchor.get("bbox", anchor)
            required = {"x1", "y1", "x2", "y2"}
            if not required.issubset(anchor_bbox):
                continue
            tolerance = self.bbox_tolerance
            if (
                bbox["x1"] >= float(anchor_bbox["x1"]) - tolerance
                and bbox["y1"] >= float(anchor_bbox["y1"]) - tolerance
                and bbox["x2"] <= float(anchor_bbox["x2"]) + tolerance
                and bbox["y2"] <= float(anchor_bbox["y2"]) + tolerance
            ):
                return True
        return False

    @staticmethod
    def _issue(code: str, message: str, field: str | None = None) -> CitationValidationIssue:
        return CitationValidationIssue(code=code, message=message, field=field)

from __future__ import annotations

from dataclasses import dataclass

import fitz

from app.config.settings import Settings
from app.exceptions import AppError
from app.extraction.types import ExtractedBlock, ExtractedPage, ExtractedTable
from app.model.documents import DocumentType


@dataclass(frozen=True, slots=True)
class PdfPageInspection:
    page_index: int
    text_character_count: int
    has_text_layer: bool
    image_only: bool
    needs_ocr: bool


@dataclass(frozen=True, slots=True)
class PdfClassification:
    document_type: DocumentType
    total_pages: int
    text_page_ratio: float
    image_only_page_ratio: float
    pages: tuple[PdfPageInspection, ...]


class PdfClassifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def classify(self, pdf_bytes: bytes) -> PdfClassification:
        try:
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        except (fitz.FileDataError, RuntimeError, ValueError) as exc:
            raise AppError(
                status_code=422,
                code="INVALID_PDF",
                message="Không thể đọc cấu trúc PDF.",
            ) from exc
        try:
            if pdf.page_count == 0:
                raise AppError(
                    status_code=422,
                    code="EMPTY_PDF",
                    message="PDF không chứa trang nào.",
                )
            pages: list[PdfPageInspection] = []
            for page_index, page in enumerate(pdf):
                text_count = len("".join(page.get_text("text").split()))
                has_text = text_count >= self.settings.pdf_text_min_characters
                has_images = bool(page.get_images(full=True))
                image_only = has_images and not has_text
                pages.append(
                    PdfPageInspection(
                        page_index=page_index,
                        text_character_count=text_count,
                        has_text_layer=has_text,
                        image_only=image_only,
                        needs_ocr=not has_text,
                    )
                )

            total = len(pages)
            text_pages = sum(page.has_text_layer for page in pages)
            image_pages = sum(page.image_only for page in pages)
            text_ratio = text_pages / total
            image_ratio = image_pages / total
            if text_pages == total:
                document_type = DocumentType.TEXT_BASED
            elif text_pages == 0:
                document_type = DocumentType.SCANNED
            else:
                document_type = DocumentType.HYBRID
            return PdfClassification(
                document_type=document_type,
                total_pages=total,
                text_page_ratio=text_ratio,
                image_only_page_ratio=image_ratio,
                pages=tuple(pages),
            )
        finally:
            pdf.close()


class PdfPageRenderer:
    def __init__(self, dpi: int = 150) -> None:
        self.dpi = dpi

    def render_page(self, pdf_bytes: bytes, *, page_index: int) -> bytes:
        try:
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                page = pdf.load_page(page_index)
                pixmap = page.get_pixmap(dpi=self.dpi, alpha=False)
                return pixmap.tobytes("png")
            finally:
                pdf.close()
        except (fitz.FileDataError, IndexError, RuntimeError, ValueError) as exc:
            raise AppError(
                status_code=422,
                code="PDF_RENDER_FAILED",
                message=f"Không thể render trang PDF {page_index}.",
            ) from exc


class PdfTextExtractor:
    def extract_page(
        self,
        pdf_bytes: bytes,
        *,
        page_index: int,
        inspection: PdfPageInspection,
    ) -> ExtractedPage:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = pdf.load_page(page_index)
            blocks: list[ExtractedBlock] = []
            raw = page.get_text("dict")
            order_index = 0
            for raw_block in raw.get("blocks", []):
                if raw_block.get("type") != 0:
                    continue
                lines: list[str] = []
                for line in raw_block.get("lines", []):
                    text = "".join(
                        str(span.get("text", "")) for span in line.get("spans", [])
                    ).strip()
                    if text:
                        lines.append(text)
                block_text = "\n".join(lines).strip()
                if not block_text:
                    continue
                x1, y1, x2, y2 = raw_block.get("bbox", (0, 0, 0, 0))
                blocks.append(
                    ExtractedBlock(
                        text=block_text,
                        bbox={
                            "x1": float(x1),
                            "y1": float(y1),
                            "x2": float(x2),
                            "y2": float(y2),
                        },
                        order_index=order_index,
                    )
                )
                order_index += 1
            return ExtractedPage(
                page_index=page_index,
                width=float(page.rect.width),
                height=float(page.rect.height),
                rotation=int(page.rotation),
                has_text_layer=inspection.has_text_layer,
                image_only=inspection.image_only,
                needs_ocr=inspection.needs_ocr,
                text="\n".join(block.text for block in blocks),
                blocks=blocks,
            )
        finally:
            pdf.close()


class PdfTableExtractor:
    """Use PyMuPDF's deterministic table detector when a page exposes tabular lines."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedTable]:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        tables: list[ExtractedTable] = []
        try:
            for page_index, page in enumerate(pdf):
                try:
                    found = page.find_tables()
                except (AttributeError, RuntimeError, ValueError):
                    continue
                for table in found.tables:
                    matrix = [
                        ["" if cell is None else str(cell).strip() for cell in row]
                        for row in table.extract()
                    ]
                    if not matrix:
                        continue
                    x1, y1, x2, y2 = table.bbox
                    tables.append(
                        ExtractedTable(
                            page_start=page_index,
                            page_end=page_index,
                            order_index=len(tables),
                            header_rows=matrix[:1],
                            rows=matrix[1:],
                            bounding_boxes=[
                                {
                                    "pageIndex": page_index,
                                    "bbox": {
                                        "x1": float(x1),
                                        "y1": float(y1),
                                        "x2": float(x2),
                                        "y2": float(y2),
                                    },
                                }
                            ],
                        )
                    )
            return tables
        finally:
            pdf.close()

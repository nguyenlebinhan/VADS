from __future__ import annotations

import re
import unicodedata
from io import BytesIO
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.chunking.service import LegalChunker
from app.config.settings import Settings
from app.exceptions import AppError, NotFoundError
from app.extraction.docx import DocxExtractor
from app.extraction.ocr import DifficultPageReviewer, OcrProvider
from app.extraction.pdf import PdfClassifier, PdfPageRenderer, PdfTableExtractor, PdfTextExtractor
from app.extraction.types import ExtractedBlock, ExtractedDocument, ExtractedPage
from app.model.chunking import DocumentChunk
from app.model.documents import Document, DocumentType
from app.model.extraction import DocumentPage, DocumentTable, PageBlock
from app.model.processing import ProcessingStatus, ProcessingStep
from app.model.repositories.storage import DocumentFileRepository
from app.model.structure import DocumentSection
from app.service.processing import ProcessingStateService
from app.storage.provider import StorageProvider
from app.structure.parser import LegalStructureParser


class DocumentProcessingPipeline:
    """Owner-1 pipeline from stored original file to persisted DocumentChunk rows."""

    def __init__(
        self,
        session: Session,
        *,
        storage: StorageProvider,
        ocr_provider: OcrProvider,
        settings: Settings,
        difficult_page_reviewer: DifficultPageReviewer | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.ocr_provider = ocr_provider
        self.settings = settings
        self.difficult_page_reviewer = difficult_page_reviewer
        self.state = ProcessingStateService(session)
        self.pdf_classifier = PdfClassifier(settings)
        self.pdf_renderer = PdfPageRenderer(settings.render_dpi)
        self.pdf_text_extractor = PdfTextExtractor()
        self.pdf_table_extractor = PdfTableExtractor()
        self.docx_extractor = DocxExtractor()
        self.structure_parser = LegalStructureParser()
        self.chunker = LegalChunker(
            min_tokens=settings.chunk_min_tokens,
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )

    def run(self, job_id: str) -> None:
        job = self.state.repository.get(job_id)
        if job is None:
            raise NotFoundError("PROCESSING_JOB", job_id)
        document = self.session.get(Document, job.document_id)
        if document is None or document.deleted_at is not None:
            raise NotFoundError("DOCUMENT", job.document_id)
        files = DocumentFileRepository(self.session).list_for_document(document.id)
        if not files:
            raise AppError(
                status_code=422,
                code="DOCUMENT_FILE_NOT_FOUND",
                message="Tài liệu không có tệp gốc để xử lý.",
            )

        self.state.transition(
            job_id,
            status=ProcessingStatus.PROCESSING,
            progress=max(job.progress, 1),
            current_step=ProcessingStep.VALIDATING_FILE,
            message="Đang kiểm tra tệp đã lưu",
        )
        content = self.storage.download(object_key=files[0].object_key)
        if not content:
            raise AppError(
                status_code=422,
                code="EMPTY_STORED_FILE",
                message="Tệp đã lưu không có dữ liệu.",
            )

        self._clear_previous_outputs(document.id)
        if document.file_extension == ".pdf":
            extracted, review_needed = self._process_pdf(job_id, document, content)
        elif document.file_extension == ".docx":
            extracted = self._process_docx(job_id, document, content)
            review_needed = False
        else:
            raise AppError(
                status_code=415,
                code="UNSUPPORTED_DOCUMENT_TYPE",
                message="Định dạng tài liệu không được hỗ trợ.",
            )

        pages, blocks, tables = self._persist_extraction(document.id, extracted)
        self.session.add_all([*pages, *blocks])
        self.session.flush()
        self.session.add_all(tables)
        self.session.flush()

        total_pages = len(pages)
        self.state.transition(
            job_id,
            status=ProcessingStatus.PROCESSING,
            progress=75,
            current_step=ProcessingStep.DETECTING_STRUCTURE,
            current_page=total_pages,
            total_pages=total_pages,
            message="Đang nhận diện cấu trúc pháp lý",
        )
        sections = self.structure_parser.parse(document.id, blocks)
        self.session.add_all(sections)
        self.session.flush()
        table_sections = [section for section in sections if section.section_type.value == "TABLE"]
        for table in tables:
            matching = next(
                (
                    section
                    for section in table_sections
                    if table.page_start <= section.page_start <= table.page_end
                ),
                None,
            )
            if matching is not None:
                table.section_id = matching.id

        self.state.transition(
            job_id,
            status=ProcessingStatus.PROCESSING,
            progress=90,
            current_step=ProcessingStep.CREATING_CHUNKS,
            current_page=total_pages,
            total_pages=total_pages,
            message="Đang tạo chunk có metadata nguồn",
        )
        chunks = self.chunker.build(
            document.id,
            pages=pages,
            blocks=blocks,
            sections=sections,
            tables=tables,
        )
        self.session.add_all(chunks)
        document.total_pages = total_pages
        document.document_type = DocumentType(extracted.document_type)
        self.session.commit()

        if review_needed:
            self.state.transition(
                job_id,
                status=ProcessingStatus.NEEDS_REVIEW,
                progress=100,
                current_step=ProcessingStep.COMPLETED,
                current_page=total_pages,
                total_pages=total_pages,
                message="OCR đã hoàn tất nhưng có trang cần kiểm tra thủ công",
            )
        else:
            self.state.transition(
                job_id,
                status=ProcessingStatus.COMPLETED,
                progress=100,
                current_step=ProcessingStep.COMPLETED,
                current_page=total_pages,
                total_pages=total_pages,
                message="Đã xử lý tài liệu thành công",
            )

    def _process_pdf(
        self,
        job_id: str,
        document: Document,
        content: bytes,
    ) -> tuple[ExtractedDocument, bool]:
        self.state.transition(
            job_id,
            status=ProcessingStatus.PROCESSING,
            progress=5,
            current_step=ProcessingStep.DETECTING_PDF_TYPE,
            message="Đang kiểm tra text layer và hình ảnh trong PDF",
        )
        classification = self.pdf_classifier.classify(content)
        total = classification.total_pages
        document.document_type = classification.document_type
        document.total_pages = total
        self.session.commit()

        rendered_pages: dict[int, bytes] = {}
        for index, inspection in enumerate(classification.pages):
            png = self.pdf_renderer.render_page(content, page_index=inspection.page_index)
            rendered_pages[inspection.page_index] = png
            object_key = (
                f"workspaces/{document.workspace_id}/documents/{document.id}/"
                f"pages/{inspection.page_index}.png"
            )
            self.storage.upload(
                BytesIO(png),
                object_key=object_key,
                content_type="image/png",
                metadata={"document-id": document.id, "page-index": str(inspection.page_index)},
            )
            # Keep the exact storage locator with the page record.
            progress = 5 + round(25 * (index + 1) / total)
            self.state.transition(
                job_id,
                status=ProcessingStatus.PROCESSING,
                progress=progress,
                current_step=ProcessingStep.RENDERING_PAGES,
                current_page=index + 1,
                total_pages=total,
                message=f"Đang render trang {index + 1}/{total}",
            )

        pages: list[ExtractedPage] = []
        review_needed = False
        for index, inspection in enumerate(classification.pages):
            page = self.pdf_text_extractor.extract_page(
                content,
                page_index=inspection.page_index,
                inspection=inspection,
            )
            page.rendered_png = rendered_pages[inspection.page_index]
            page.rendered_object_key = (
                f"workspaces/{document.workspace_id}/documents/{document.id}/"
                f"pages/{inspection.page_index}.png"
            )
            if inspection.needs_ocr:
                ocr = self.ocr_provider.recognize_page(
                    page.rendered_png,
                    page_index=inspection.page_index,
                )
                page.text = ocr.text
                page.ocr_confidence = ocr.average_confidence
                page.blocks = [
                    ExtractedBlock(
                        text=block.text,
                        bbox=block.bbox.model_dump(),
                        order_index=block.order_index,
                        confidence=block.confidence,
                        source="OCR",
                    )
                    for block in ocr.blocks
                ]
                if ocr.average_confidence < self.settings.ocr_review_confidence_threshold:
                    review_needed = True
                    if self.difficult_page_reviewer is not None:
                        self.difficult_page_reviewer.review_page(
                            page_index=inspection.page_index,
                            image=page.rendered_png,
                            ocr=ocr,
                        )
            pages.append(page)
            progress = 30 + round(35 * (index + 1) / total)
            self.state.transition(
                job_id,
                status=ProcessingStatus.PROCESSING,
                progress=progress,
                current_step=ProcessingStep.OCR_PROCESSING,
                current_page=index + 1,
                total_pages=total,
                message=f"Đang xử lý trang {index + 1}/{total}",
            )
        return (
            ExtractedDocument(
                document_type=classification.document_type.value,
                pages=pages,
                tables=self.pdf_table_extractor.extract(content),
            ),
            review_needed,
        )

    def _process_docx(
        self,
        job_id: str,
        document: Document,
        content: bytes,
    ) -> ExtractedDocument:
        self.state.transition(
            job_id,
            status=ProcessingStatus.PROCESSING,
            progress=10,
            current_step=ProcessingStep.DETECTING_PDF_TYPE,
            current_page=0,
            total_pages=1,
            message="Đã nhận diện tài liệu DOCX",
        )
        extracted = self.docx_extractor.extract(content)
        document.document_type = DocumentType.DOCX
        document.total_pages = len(extracted.pages)
        self.state.transition(
            job_id,
            status=ProcessingStatus.PROCESSING,
            progress=65,
            current_step=ProcessingStep.OCR_PROCESSING,
            current_page=len(extracted.pages),
            total_pages=len(extracted.pages),
            message="Đã trích xuất nội dung DOCX",
        )
        return extracted

    def _persist_extraction(
        self,
        document_id: str,
        extracted: ExtractedDocument,
    ) -> tuple[list[DocumentPage], list[PageBlock], list[DocumentTable]]:
        page_models: list[DocumentPage] = []
        block_models: list[PageBlock] = []
        for page in extracted.pages:
            page_model = DocumentPage(
                id=str(uuid4()),
                document_id=document_id,
                page_index=page.page_index,
                printed_page_number=page.page_index + 1,
                width=page.width,
                height=page.height,
                rotation=page.rotation,
                has_text_layer=page.has_text_layer,
                image_only=page.image_only,
                needs_ocr=page.needs_ocr,
                extracted_text=page.text,
                rendered_object_key=page.rendered_object_key,
                ocr_confidence=page.ocr_confidence,
            )
            for block in page.blocks:
                block_model = PageBlock(
                    id=str(uuid4()),
                    document_id=document_id,
                    page=page_model,
                    order_index=block.order_index,
                    block_type=block.block_type,
                    text=block.text,
                    normalized_text=self._normalize(block.text),
                    bbox=block.bbox,
                    confidence=block.confidence,
                    source=block.source,
                )
                block_models.append(block_model)
            page_models.append(page_model)

        table_models: list[DocumentTable] = []
        for table in extracted.tables:
            anchors = [
                block
                for block in block_models
                if table.page_start <= block.page.page_index <= table.page_end
            ]
            anchor = anchors[0] if anchors else (block_models[0] if block_models else None)
            table_models.append(
                DocumentTable(
                    document_id=document_id,
                    page_start=table.page_start,
                    page_end=table.page_end,
                    order_index=table.order_index,
                    title=table.title,
                    start_block_id=anchor.id if anchor else None,
                    end_block_id=(anchors[-1].id if anchors else (anchor.id if anchor else None)),
                    bounding_boxes=table.bounding_boxes,
                    header_rows=table.header_rows,
                    rows=table.rows,
                )
            )
        return page_models, block_models, table_models

    def _clear_previous_outputs(self, document_id: str) -> None:
        for model in (
            DocumentChunk,
            DocumentTable,
            DocumentSection,
            PageBlock,
            DocumentPage,
        ):
            self.session.execute(delete(model).where(model.document_id == document_id))
        self.session.commit()

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[ \t]+", " ", unicodedata.normalize("NFC", value)).strip()

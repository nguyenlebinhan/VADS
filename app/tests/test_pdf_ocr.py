import pytest

from app.common.contracts import BoundingBox
from app.extraction.ocr import MockOcrProvider, PaddleOcrProvider
from app.extraction.pdf import PdfClassifier
from app.extraction.schemas import OcrBlock, OcrPageResult
from app.model.documents import DocumentType
from app.tests.helpers import pdf_with_pages


def test_pdf_classifier_detects_text_pdf(test_settings) -> None:
    content = pdf_with_pages(
        ["ARTICLE ONE\nThis page contains a sufficiently long searchable text layer."]
    )

    result = PdfClassifier(test_settings).classify(content)

    assert result.document_type == DocumentType.TEXT_BASED
    assert result.text_page_ratio == 1
    assert result.pages[0].needs_ocr is False


def test_pdf_classifier_detects_scanned_pdf(test_settings) -> None:
    result = PdfClassifier(test_settings).classify(pdf_with_pages([None, None]))

    assert result.document_type == DocumentType.SCANNED
    assert result.text_page_ratio == 0
    assert all(page.needs_ocr for page in result.pages)


def test_pdf_classifier_detects_hybrid_pdf(test_settings) -> None:
    content = pdf_with_pages(
        ["This page contains a sufficiently long searchable text layer.", None]
    )

    result = PdfClassifier(test_settings).classify(content)

    assert result.document_type == DocumentType.HYBRID
    assert [page.needs_ocr for page in result.pages] == [False, True]


def test_ocr_page_and_region_are_deterministic() -> None:
    page_result = OcrPageResult(
        page_index=0,
        text="Điều 1. Phạm vi điều chỉnh",
        average_confidence=0.98,
        blocks=[
            OcrBlock(
                text="Điều 1. Phạm vi điều chỉnh",
                confidence=0.98,
                bbox=BoundingBox(x1=110, y1=202, x2=810, y2=245),
                order_index=4,
            )
        ],
    )
    provider = MockOcrProvider({0: page_result})

    full = provider.recognize_page(b"png", page_index=0)
    region = provider.recognize_region(
        b"png",
        page_index=0,
        region=BoundingBox(x1=100, y1=190, x2=820, y2=260),
    )

    assert full.average_confidence == 0.98
    assert full.blocks[0].bbox.x1 == 110
    assert region.text == page_result.text
    assert provider.health_check().healthy is True


def test_paddle_ocr_v3_prediction_is_mapped_to_contract() -> None:
    class Prediction:
        json = {
            "res": {
                "rec_texts": ["Điều 1. Phạm vi điều chỉnh", "Khoản 1"],
                "rec_scores": [0.98, 0.91],
                "rec_boxes": [[110, 202, 810, 245], [120, 260, 300, 295]],
            }
        }

    class Engine:
        def predict(self, image):
            assert image == "decoded-image"
            return [Prediction()]

    provider = PaddleOcrProvider(
        engine=Engine(),
        image_decoder=lambda image: "decoded-image",
    )

    result = provider.recognize_page(b"png", page_index=4)

    assert result.page_index == 4
    assert result.text == "Điều 1. Phạm vi điều chỉnh\nKhoản 1"
    assert result.average_confidence == pytest.approx(0.945)
    assert result.blocks[0].bbox == BoundingBox(x1=110, y1=202, x2=810, y2=245)
    assert result.blocks[1].order_index == 1
    assert result.metadata["ocrVersion"] == "PP-OCRv3"

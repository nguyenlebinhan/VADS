from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Protocol

from app.common.contracts import BoundingBox
from app.extraction.schemas import OcrBlock, OcrHealth, OcrPageResult


class OcrProvider(ABC):
    """OCR engine boundary. Implementations must not depend on business services."""

    @abstractmethod
    def recognize_page(self, image: bytes, *, page_index: int) -> OcrPageResult:
        raise NotImplementedError

    @abstractmethod
    def recognize_region(
        self,
        image: bytes,
        *,
        page_index: int,
        region: BoundingBox,
    ) -> OcrPageResult:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> OcrHealth:
        raise NotImplementedError


class DifficultPageReviewer(Protocol):
    """Extension point owned by model orchestration, not an OCR implementation."""

    def review_page(self, *, page_index: int, image: bytes, ocr: OcrPageResult) -> None: ...


class MockOcrProvider(OcrProvider):
    """Deterministic provider used for local development and unit tests."""

    def __init__(self, results: Mapping[int, OcrPageResult] | None = None) -> None:
        self.results = dict(results or {})

    def recognize_page(self, image: bytes, *, page_index: int) -> OcrPageResult:
        del image
        return self.results.get(
            page_index,
            OcrPageResult(
                page_index=page_index,
                text="",
                average_confidence=0,
                blocks=[],
                metadata={"provider": "mock", "configuredResult": False},
            ),
        )

    def recognize_region(
        self,
        image: bytes,
        *,
        page_index: int,
        region: BoundingBox,
    ) -> OcrPageResult:
        result = self.recognize_page(image, page_index=page_index)
        selected = [block for block in result.blocks if _intersects(block.bbox, region)]
        confidence = sum(block.confidence for block in selected) / len(selected) if selected else 0
        return OcrPageResult(
            page_index=page_index,
            text="\n".join(block.text for block in selected),
            average_confidence=confidence,
            blocks=selected,
            metadata={"provider": "mock", "region": region.model_dump(by_alias=True)},
        )

    def health_check(self) -> OcrHealth:
        return OcrHealth(healthy=True, provider="MOCK")


class PaddleOcrProvider(OcrProvider):
    """Optional PaddleOCR adapter loaded lazily when the extra is installed."""

    def __init__(self, *, language: str = "vi") -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed; install the optional OCR runtime or use MOCK"
            ) from exc
        self._engine = PaddleOCR(use_angle_cls=True, lang=language, show_log=False)

    def recognize_page(self, image: bytes, *, page_index: int) -> OcrPageResult:
        result = self._engine.ocr(image, cls=True)
        blocks: list[OcrBlock] = []
        for order_index, item in enumerate((result[0] if result else []) or []):
            points, recognition = item
            text, confidence = recognition
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            blocks.append(
                OcrBlock(
                    text=str(text),
                    confidence=float(confidence),
                    bbox=BoundingBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys)),
                    order_index=order_index,
                )
            )
        average = sum(block.confidence for block in blocks) / len(blocks) if blocks else 0
        return OcrPageResult(
            page_index=page_index,
            text="\n".join(block.text for block in blocks),
            average_confidence=average,
            blocks=blocks,
            metadata={"provider": "PADDLEOCR"},
        )

    def recognize_region(
        self,
        image: bytes,
        *,
        page_index: int,
        region: BoundingBox,
    ) -> OcrPageResult:
        result = self.recognize_page(image, page_index=page_index)
        selected = [block for block in result.blocks if _intersects(block.bbox, region)]
        confidence = sum(block.confidence for block in selected) / len(selected) if selected else 0
        return OcrPageResult(
            page_index=page_index,
            text="\n".join(block.text for block in selected),
            average_confidence=confidence,
            blocks=selected,
            metadata={"provider": "PADDLEOCR", "region": region.model_dump(by_alias=True)},
        )

    def health_check(self) -> OcrHealth:
        return OcrHealth(healthy=True, provider="PADDLEOCR")


def _intersects(first: BoundingBox, second: BoundingBox) -> bool:
    return not (
        first.x2 < second.x1 or first.x1 > second.x2 or first.y2 < second.y1 or first.y1 > second.y2
    )

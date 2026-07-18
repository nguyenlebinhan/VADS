from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Protocol

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
    """PaddleOCR 3.x adapter loaded only by the document worker."""

    def __init__(
        self,
        *,
        language: str = "vi",
        engine: Any | None = None,
        image_decoder: Callable[[bytes], Any] | None = None,
    ) -> None:
        self._language = language
        self._ocr_version = "PP-OCRv3"
        self._image_decoder = image_decoder or _decode_image
        if engine is None:
            try:
                from paddleocr import PaddleOCR  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError(
                    "PaddleOCR is not installed in the worker image; rebuild the worker "
                    "with INSTALL_OCR=true or use MOCK"
                ) from exc
            engine = PaddleOCR(
                lang=language,
                ocr_version=self._ocr_version,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device="cpu",
                cpu_threads=4,
            )
        self._engine = engine

    def recognize_page(self, image: bytes, *, page_index: int) -> OcrPageResult:
        decoded_image = self._image_decoder(image)
        predictions = self._engine.predict(decoded_image)
        blocks: list[OcrBlock] = []
        for prediction in predictions or []:
            payload = _prediction_payload(prediction)
            texts = _as_sequence(payload.get("rec_texts"))
            scores = _as_sequence(payload.get("rec_scores"))
            boxes = _as_sequence(payload.get("rec_boxes"))
            polygons = _as_sequence(payload.get("rec_polys"))
            for item_index, raw_text in enumerate(texts):
                text = str(raw_text).strip()
                if not text:
                    continue
                confidence = _confidence_at(scores, item_index)
                bbox = _bbox_at(boxes, polygons, item_index)
                if bbox is None:
                    continue
                blocks.append(
                    OcrBlock(
                        text=text,
                        confidence=confidence,
                        bbox=bbox,
                        order_index=len(blocks),
                    )
                )
        average = sum(block.confidence for block in blocks) / len(blocks) if blocks else 0
        return OcrPageResult(
            page_index=page_index,
            text="\n".join(block.text for block in blocks),
            average_confidence=average,
            blocks=blocks,
            metadata={
                "provider": "PADDLEOCR",
                "language": self._language,
                "ocrVersion": self._ocr_version,
            },
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
        return OcrHealth(
            healthy=True,
            provider="PADDLEOCR",
            details={
                "paddleocrVersion": _package_version("paddleocr"),
                "paddlepaddleVersion": _package_version("paddlepaddle"),
                "language": self._language,
                "ocrVersion": self._ocr_version,
            },
        )


def _decode_image(image: bytes) -> Any:
    if not image:
        raise ValueError("OCR image cannot be empty")
    try:
        import cv2  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("PaddleOCR image dependencies are not installed") from exc
    encoded = np.frombuffer(image, dtype=np.uint8)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError("OCR image is not a valid encoded image")
    return decoded


def _prediction_payload(prediction: Any) -> Mapping[str, Any]:
    raw = getattr(prediction, "json", prediction)
    if callable(raw):
        raw = raw()
    if not isinstance(raw, Mapping):
        raise RuntimeError("PaddleOCR returned an unsupported prediction payload")
    result = raw.get("res", raw)
    if not isinstance(result, Mapping):
        raise RuntimeError("PaddleOCR prediction does not contain a result mapping")
    return result


def _as_sequence(value: Any) -> Sequence[Any]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    try:
        return tuple(value)
    except TypeError:
        return ()


def _confidence_at(scores: Sequence[Any], index: int) -> float:
    if index >= len(scores):
        return 0
    return min(1.0, max(0.0, float(scores[index])))


def _bbox_at(
    boxes: Sequence[Any],
    polygons: Sequence[Any],
    index: int,
) -> BoundingBox | None:
    if index < len(boxes):
        box = _as_sequence(boxes[index])
        if len(box) >= 4:
            return BoundingBox(
                x1=float(box[0]),
                y1=float(box[1]),
                x2=float(box[2]),
                y2=float(box[3]),
            )
    if index < len(polygons):
        points = [_as_sequence(point) for point in _as_sequence(polygons[index])]
        xs = [float(point[0]) for point in points if len(point) >= 2]
        ys = [float(point[1]) for point in points if len(point) >= 2]
        if xs and ys:
            return BoundingBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))
    return None


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _intersects(first: BoundingBox, second: BoundingBox) -> bool:
    return not (
        first.x2 < second.x1 or first.x1 > second.x2 or first.y2 < second.y1 or first.y1 > second.y2
    )

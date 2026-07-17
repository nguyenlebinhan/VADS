from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExtractedBlock:
    text: str
    bbox: dict[str, float]
    order_index: int
    confidence: float | None = None
    block_type: str = "PARAGRAPH"
    source: str = "TEXT_LAYER"


@dataclass(slots=True)
class ExtractedTable:
    page_start: int
    page_end: int
    order_index: int
    header_rows: list[list[str]] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    title: str | None = None
    bounding_boxes: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ExtractedPage:
    page_index: int
    width: float
    height: float
    rotation: int
    has_text_layer: bool
    image_only: bool
    needs_ocr: bool
    text: str
    blocks: list[ExtractedBlock] = field(default_factory=list)
    ocr_confidence: float | None = None
    rendered_png: bytes | None = None
    rendered_object_key: str | None = None


@dataclass(slots=True)
class ExtractedDocument:
    document_type: str
    pages: list[ExtractedPage]
    tables: list[ExtractedTable] = field(default_factory=list)

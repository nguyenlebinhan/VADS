from typing import Any

from pydantic import Field

from app.common.contracts import APIModel, BoundingBox


class OcrBlock(APIModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: BoundingBox
    order_index: int = Field(ge=0)


class OcrPageResult(APIModel):
    page_index: int = Field(ge=0)
    text: str
    average_confidence: float = Field(ge=0, le=1)
    blocks: list[OcrBlock] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OcrHealth(APIModel):
    healthy: bool
    provider: str
    details: dict[str, Any] = Field(default_factory=dict)

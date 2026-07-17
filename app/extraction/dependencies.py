from app.config.settings import Settings
from app.extraction.ocr import MockOcrProvider, OcrProvider, PaddleOcrProvider


def build_ocr_provider(settings: Settings) -> OcrProvider:
    if settings.ocr_provider == "PADDLEOCR":
        return PaddleOcrProvider(language="vi")
    return MockOcrProvider()

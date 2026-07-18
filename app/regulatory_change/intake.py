from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

import fitz
from docx import Document as WordDocument

from app.exceptions import AppError


@dataclass(frozen=True, slots=True)
class ParsedRegulatorySection:
    section_type: str
    label: str | None
    title: str | None
    legal_location: str
    content: str
    order_index: int
    page_start: int | None = None
    page_end: int | None = None


class RegulatoryDocumentIntakeAgent:
    _heading = re.compile(
        r"^(?P<type>Chương|Mục|Điều|Khoản|Điểm|Phụ\s*lục)\s+"
        r"(?P<label>[^.\-:]+)(?:[.\-:]\s*(?P<title>.*))?$",
        re.IGNORECASE,
    )

    def extract_text(self, content: bytes, *, filename: str, mime_type: str) -> str:
        lower_name = filename.casefold()
        try:
            if mime_type == "application/pdf" or lower_name.endswith(".pdf"):
                document = fitz.open(stream=content, filetype="pdf")
                try:
                    text = "\n".join(page.get_text("text") for page in document)
                finally:
                    document.close()
            elif (
                mime_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                or lower_name.endswith(".docx")
            ):
                document = WordDocument(BytesIO(content))
                text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            else:
                raise AppError(
                    status_code=422,
                    code="UNSUPPORTED_REGULATORY_FILE",
                    message="Chỉ hỗ trợ tài liệu PDF hoặc DOCX.",
                )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                status_code=422,
                code="REGULATORY_PARSE_FAILED",
                message="Không thể đọc nội dung tài liệu.",
            ) from exc
        normalized = text.replace("\x00", "").strip()
        if not normalized:
            raise AppError(
                status_code=422,
                code="REGULATORY_OCR_REQUIRED",
                message="Tài liệu không có text layer; cần hoàn thành OCR trước khi phân tích.",
            )
        return normalized

    def parse_sections(self, text: str) -> list[ParsedRegulatorySection]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections: list[ParsedRegulatorySection] = []
        current_heading: tuple[str, str | None, str | None, str] | None = None
        content_lines: list[str] = []
        hierarchy: dict[str, str] = {}

        def flush() -> None:
            if not content_lines and current_heading is None:
                return
            if current_heading is None:
                section_type, label, title, location = "PREAMBLE", None, None, "Mở đầu"
            else:
                section_type, label, title, location = current_heading
            content = "\n".join(content_lines).strip() or location
            sections.append(
                ParsedRegulatorySection(
                    section_type=section_type,
                    label=label,
                    title=title,
                    legal_location=location,
                    content=content,
                    order_index=len(sections),
                )
            )

        for line in lines:
            match = self._heading.match(line)
            if match:
                flush()
                content_lines = []
                raw_type = match.group("type")
                label = match.group("label").strip()
                title = (match.group("title") or "").strip() or None
                type_key = self._normalize(raw_type).upper().replace("-", "_")
                display_type = raw_type.title()
                reset_children = {
                    "CHUONG": ("MUC", "DIEU", "KHOAN", "DIEM"),
                    "MUC": ("DIEU", "KHOAN", "DIEM"),
                    "DIEU": ("KHOAN", "DIEM"),
                    "KHOAN": ("DIEM",),
                    "DIEM": (),
                    "PHU_LUC": ("CHUONG", "MUC", "DIEU", "KHOAN", "DIEM"),
                }
                for child in reset_children.get(type_key, ()):
                    hierarchy.pop(child, None)
                hierarchy[type_key] = f"{display_type} {label}"
                location_order = ("DIEM", "KHOAN", "DIEU", "MUC", "CHUONG", "PHU_LUC")
                location = ", ".join(
                    hierarchy[item] for item in location_order if item in hierarchy
                )
                current_heading = (
                    type_key,
                    label,
                    title,
                    location,
                )
            else:
                content_lines.append(line)
        flush()
        if not sections:
            sections.append(
                ParsedRegulatorySection(
                    section_type="DOCUMENT",
                    label=None,
                    title=None,
                    legal_location="Toàn văn",
                    content=text,
                    order_index=0,
                )
            )
        return sections

    @staticmethod
    def executive_summary(text: str) -> str:
        collapsed = re.sub(r"\s+", " ", text).strip()
        if len(collapsed) <= 700:
            return collapsed
        return f"{collapsed[:697].rstrip()}..."

    @staticmethod
    def family_key(title: str, document_number: str, explicit: str | None) -> str:
        if explicit and explicit.strip():
            return RegulatoryDocumentIntakeAgent._normalize(explicit)[:255]
        without_year = re.sub(r"\b(?:19|20)\d{2}\b", "", f"{document_number} {title}")
        return RegulatoryDocumentIntakeAgent._normalize(without_year)[:255]

    @staticmethod
    def _normalize(value: str) -> str:
        value = value.replace("Đ", "D").replace("đ", "d")
        ascii_value = unicodedata.normalize("NFD", value)
        ascii_value = "".join(char for char in ascii_value if unicodedata.category(char) != "Mn")
        return re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")

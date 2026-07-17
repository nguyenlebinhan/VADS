from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from app.model.extraction import PageBlock
from app.model.structure import DocumentSection, SectionType


@dataclass(frozen=True, slots=True)
class HeadingMatch:
    section_type: SectionType
    label: str | None
    title: str | None
    level: int


class LegalStructureParser:
    """Vietnamese legal-document parser using deterministic rules before AI."""

    _chapter = re.compile(r"^\s*CHƯƠNG\s+([IVXLCDM]+|\d+)\s*[.\-:]?\s*(.*)$", re.IGNORECASE)
    _section = re.compile(r"^\s*MỤC\s+(\d+[A-Z]?)\s*[.\-:]?\s*(.*)$", re.IGNORECASE)
    _article = re.compile(r"^\s*ĐIỀU\s+(\d+[A-Z]?)\s*[.]?\s*(.*)$", re.IGNORECASE)
    _clause = re.compile(r"^\s*(\d+)\s*[.)]\s+(.+)$")
    _point = re.compile(r"^\s*([a-zđ])\s*[)]\s+(.+)$", re.IGNORECASE)
    _subpoint = re.compile(r"^\s*\(([ivxlcdm]+)\)\s+(.+)$", re.IGNORECASE)
    _appendix = re.compile(r"^\s*PHỤ\s+LỤC(?:\s+([IVXLCDM\d]+))?\b\s*(.*)$", re.IGNORECASE)
    _form = re.compile(r"^\s*MẪU\s+SỐ\s+([\w.\-/]+)\s*(.*)$", re.IGNORECASE)
    _document_number = re.compile(r"^\s*SỐ\s*:\s*(.+)$", re.IGNORECASE)
    _issued_date = re.compile(r".*ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}.*", re.IGNORECASE)
    _legal_basis = re.compile(r"^\s*CĂN\s+CỨ\b", re.IGNORECASE)
    _authority = re.compile(
        r"^\s*(?:CHÍNH\s+PHỦ|BỘ\s+[A-ZÀ-Ỹ ]+|ỦY\s+BAN\s+NHÂN\s+DÂN|"
        r"HỘI\s+ĐỒNG\s+NHÂN\s+DÂN|QUỐC\s+HỘI|TÒA\s+ÁN\s+NHÂN\s+DÂN)\b",
        re.IGNORECASE,
    )
    _table = re.compile(r"^\s*BẢNG(?:\s+SỐ)?\s+[\w.\-/]+\b", re.IGNORECASE)
    _recipient = re.compile(r"^\s*NƠI\s+NHẬN\s*:", re.IGNORECASE)
    _signature = re.compile(
        r"^\s*(?:TM\.|KT\.|TL\.|TUQ\.|CHỦ\s+TỊCH|BỘ\s+TRƯỞNG|GIÁM\s+ĐỐC)\b",
        re.IGNORECASE,
    )

    _hierarchy = {
        SectionType.DOCUMENT_TITLE: 0,
        SectionType.DOCUMENT_NUMBER: 0,
        SectionType.ISSUING_AUTHORITY: 0,
        SectionType.ISSUED_DATE: 0,
        SectionType.LEGAL_BASIS: 0,
        SectionType.PREAMBLE: 0,
        SectionType.CHAPTER: 1,
        SectionType.APPENDIX: 1,
        SectionType.SECTION: 2,
        SectionType.FORM: 2,
        SectionType.ARTICLE: 3,
        SectionType.CLAUSE: 4,
        SectionType.POINT: 5,
        SectionType.SUBPOINT: 6,
        SectionType.TABLE: 7,
        SectionType.SIGNATURE: 1,
        SectionType.RECIPIENT_LIST: 1,
        SectionType.PARAGRAPH: 7,
    }

    def parse(self, document_id: str, blocks: list[PageBlock]) -> list[DocumentSection]:
        ordered = sorted(blocks, key=lambda block: (block.page.page_index, block.order_index))
        sections: list[DocumentSection] = []
        active_by_level: dict[int, DocumentSection] = {}
        current: DocumentSection | None = None

        for absolute_order, block in enumerate(ordered):
            text = block.text.strip()
            if not text:
                continue
            match = (
                HeadingMatch(SectionType.TABLE, "Bảng", None, 7)
                if block.block_type == "TABLE"
                else self.classify(text, order_index=absolute_order)
            )
            page_index = block.page.page_index

            if match is None:
                # Content on a new page remains in the same active hierarchy.
                for active in active_by_level.values():
                    active.end_block_id = block.id
                    active.page_end = page_index
                if current is not None:
                    current.content = "\n".join(part for part in (current.content, text) if part)
                    current.end_block_id = block.id
                    current.page_end = page_index
                continue

            # A child heading extends its ancestors. A sibling/new ancestor must
            # not be included in the previous section's range.
            for level, active in active_by_level.items():
                if level < match.level:
                    active.end_block_id = block.id
                    active.page_end = page_index

            block.block_type = match.section_type.value
            for level in [level for level in active_by_level if level >= match.level]:
                del active_by_level[level]
            parent = self._nearest_parent(active_by_level, match.level)
            section_id = str(uuid4())
            heading_path = [] if parent is None else [*parent.heading_path]
            heading_path.append(
                {
                    "id": section_id,
                    "sectionType": match.section_type.value,
                    "label": match.label,
                    "title": match.title,
                }
            )
            section = DocumentSection(
                id=section_id,
                document_id=document_id,
                parent_id=parent.id if parent else None,
                section_type=match.section_type,
                label=match.label,
                title=match.title,
                content=text,
                hierarchy_level=match.level,
                order_index=len(sections),
                page_start=page_index,
                page_end=page_index,
                start_block_id=block.id,
                end_block_id=block.id,
                heading_path=heading_path,
            )
            sections.append(section)
            active_by_level[match.level] = section
            current = section

        return sections

    def classify(self, text: str, *, order_index: int = 0) -> HeadingMatch | None:
        normalized = " ".join(text.split())
        if match := self._chapter.match(normalized):
            return HeadingMatch(
                SectionType.CHAPTER,
                f"Chương {match.group(1).upper()}",
                match.group(2).strip() or None,
                1,
            )
        if match := self._section.match(normalized):
            return HeadingMatch(
                SectionType.SECTION,
                f"Mục {match.group(1)}",
                match.group(2).strip() or None,
                2,
            )
        if match := self._article.match(normalized):
            return HeadingMatch(
                SectionType.ARTICLE,
                f"Điều {match.group(1)}",
                match.group(2).strip() or None,
                3,
            )
        if match := self._clause.match(normalized):
            return HeadingMatch(
                SectionType.CLAUSE,
                f"Khoản {match.group(1)}",
                match.group(2).strip() or None,
                4,
            )
        if match := self._point.match(normalized):
            return HeadingMatch(
                SectionType.POINT,
                f"Điểm {match.group(1).lower()}",
                match.group(2).strip() or None,
                5,
            )
        if match := self._subpoint.match(normalized):
            return HeadingMatch(
                SectionType.SUBPOINT,
                f"Tiểu điểm ({match.group(1).lower()})",
                match.group(2).strip() or None,
                6,
            )
        if match := self._appendix.match(normalized):
            suffix = f" {match.group(1)}" if match.group(1) else ""
            return HeadingMatch(
                SectionType.APPENDIX,
                f"Phụ lục{suffix}",
                match.group(2).strip() or None,
                1,
            )
        if match := self._form.match(normalized):
            return HeadingMatch(
                SectionType.FORM,
                f"Mẫu số {match.group(1)}",
                match.group(2).strip() or None,
                2,
            )
        if match := self._document_number.match(normalized):
            return HeadingMatch(SectionType.DOCUMENT_NUMBER, f"Số: {match.group(1)}", None, 0)
        if self._issued_date.match(normalized):
            return HeadingMatch(SectionType.ISSUED_DATE, normalized, None, 0)
        if self._legal_basis.match(normalized):
            return HeadingMatch(SectionType.LEGAL_BASIS, "Căn cứ", normalized, 0)
        if self._authority.match(normalized):
            return HeadingMatch(SectionType.ISSUING_AUTHORITY, normalized, None, 0)
        if self._table.match(normalized):
            return HeadingMatch(SectionType.TABLE, normalized, None, 7)
        if self._recipient.match(normalized):
            return HeadingMatch(SectionType.RECIPIENT_LIST, "Nơi nhận", None, 1)
        if self._signature.match(normalized):
            return HeadingMatch(SectionType.SIGNATURE, normalized, None, 1)
        if normalized.upper() in {"QUYẾT ĐỊNH:", "QUYẾT ĐỊNH", "NGHỊ ĐỊNH:"}:
            return HeadingMatch(SectionType.PREAMBLE, normalized, None, 0)
        if order_index < 8 and self._looks_like_title(normalized):
            return HeadingMatch(SectionType.DOCUMENT_TITLE, normalized, None, 0)
        return None

    @staticmethod
    def _nearest_parent(
        active_by_level: dict[int, DocumentSection], level: int
    ) -> DocumentSection | None:
        candidates = [
            candidate_level for candidate_level in active_by_level if candidate_level < level
        ]
        return active_by_level[max(candidates)] if candidates else None

    @staticmethod
    def _looks_like_title(text: str) -> bool:
        letters = [character for character in text if character.isalpha()]
        return (
            bool(letters)
            and len(text) <= 250
            and all(not character.islower() for character in letters)
        )

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.model.chunking import DocumentChunk
from app.model.extraction import DocumentPage, DocumentTable, PageBlock
from app.model.structure import DocumentSection, SectionType


@dataclass(slots=True)
class ChunkPart:
    content: str
    blocks: list[PageBlock]
    token_count: int


class LegalChunker:
    """Hierarchy-aware chunking that never crosses article boundaries."""

    def __init__(
        self, *, min_tokens: int = 300, max_tokens: int = 800, overlap_tokens: int = 75
    ) -> None:
        if min_tokens > max_tokens:
            raise ValueError("min_tokens must not exceed max_tokens")
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def build(
        self,
        document_id: str,
        *,
        pages: list[DocumentPage],
        blocks: list[PageBlock],
        sections: list[DocumentSection],
        tables: list[DocumentTable] | None = None,
    ) -> list[DocumentChunk]:
        ordered_blocks = sorted(
            blocks, key=lambda block: (block.page.page_index, block.order_index)
        )
        position = {block.id: index for index, block in enumerate(ordered_blocks)}
        page_by_index = {page.page_index: page for page in pages}
        article_sections = [
            section for section in sections if section.section_type == SectionType.ARTICLE
        ]
        root_candidates = article_sections or [
            section
            for section in sections
            if section.section_type in {SectionType.APPENDIX, SectionType.FORM}
        ]

        chunks: list[DocumentChunk] = []
        if root_candidates:
            for root in root_candidates:
                root_blocks = self._blocks_for_section(root, ordered_blocks, position)
                if not root_blocks:
                    continue
                if self._count_tokens(self._join(root_blocks)) <= self.max_tokens:
                    self._append_parts(
                        chunks,
                        document_id,
                        root,
                        [self._one_part(root_blocks)],
                        page_by_index,
                    )
                    continue
                children = [
                    section
                    for section in sections
                    if section.parent_id == root.id
                    and section.section_type in {SectionType.CLAUSE, SectionType.POINT}
                ]
                if children:
                    for child in children:
                        child_blocks = self._blocks_for_section(child, ordered_blocks, position)
                        self._append_parts(
                            chunks,
                            document_id,
                            child,
                            self._split(child_blocks),
                            page_by_index,
                        )
                else:
                    self._append_parts(
                        chunks,
                        document_id,
                        root,
                        self._split(root_blocks),
                        page_by_index,
                    )
        elif ordered_blocks:
            self._append_parts(
                chunks,
                document_id,
                None,
                self._split(ordered_blocks),
                page_by_index,
            )

        for table in tables or []:
            content = self._table_text(table)
            if not content:
                continue
            start_block = next(
                (block for block in ordered_blocks if block.id == table.start_block_id), None
            )
            end_block = next(
                (block for block in ordered_blocks if block.id == table.end_block_id), None
            )
            anchor = start_block or end_block
            if anchor is None:
                continue
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    section_id=table.section_id,
                    order_index=len(chunks),
                    chunk_type="TABLE",
                    content=content,
                    normalized_content=self._normalize(content),
                    pdf_page_start=table.page_start,
                    pdf_page_end=table.page_end,
                    printed_page_start=self._printed_page(page_by_index, table.page_start),
                    printed_page_end=self._printed_page(page_by_index, table.page_end),
                    start_block_id=anchor.id,
                    end_block_id=(end_block or anchor).id,
                    bounding_boxes=table.bounding_boxes,
                    token_count=self._count_tokens(content),
                )
            )
        return chunks

    def _append_parts(
        self,
        target: list[DocumentChunk],
        document_id: str,
        section: DocumentSection | None,
        parts: list[ChunkPart],
        pages: dict[int, DocumentPage],
    ) -> None:
        metadata = self._heading_metadata(section)
        for part in parts:
            if not part.blocks or not part.content.strip():
                continue
            start = part.blocks[0]
            end = part.blocks[-1]
            start_page = start.page.page_index
            end_page = end.page.page_index
            confidences = [
                block.confidence for block in part.blocks if block.confidence is not None
            ]
            target.append(
                DocumentChunk(
                    document_id=document_id,
                    section_id=section.id if section else None,
                    order_index=len(target),
                    chunk_type=self._chunk_type(section),
                    content=part.content,
                    normalized_content=self._normalize(part.content),
                    pdf_page_start=start_page,
                    pdf_page_end=end_page,
                    printed_page_start=self._printed_page(pages, start_page),
                    printed_page_end=self._printed_page(pages, end_page),
                    start_block_id=start.id,
                    end_block_id=end.id,
                    bounding_boxes=[
                        {"pageIndex": block.page.page_index, "bbox": block.bbox}
                        for block in part.blocks
                    ],
                    ocr_confidence=(sum(confidences) / len(confidences) if confidences else None),
                    token_count=part.token_count,
                    **metadata,
                )
            )

    def _split(self, blocks: list[PageBlock]) -> list[ChunkPart]:
        if not blocks:
            return []
        parts: list[ChunkPart] = []
        current: list[PageBlock] = []
        current_tokens = 0
        for block in blocks:
            block_tokens = self._count_tokens(block.text)
            if block_tokens > self.max_tokens:
                if current:
                    parts.append(self._one_part(current))
                    current = []
                    current_tokens = 0
                parts.extend(self._split_large_block(block))
                continue
            if current and current_tokens + block_tokens > self.max_tokens:
                parts.append(self._one_part(current))
                current = self._overlap_blocks(current)
                current_tokens = self._count_tokens(self._join(current))
            current.append(block)
            current_tokens += block_tokens
        if current:
            parts.append(self._one_part(current))
        return parts

    def _split_large_block(self, block: PageBlock) -> list[ChunkPart]:
        words = block.text.split()
        if not words:
            return []
        overlap = min(self.overlap_tokens, max(0, self.max_tokens - 1))
        step = max(1, self.max_tokens - overlap)
        parts: list[ChunkPart] = []
        for start in range(0, len(words), step):
            content = " ".join(words[start : start + self.max_tokens])
            if not content:
                break
            parts.append(
                ChunkPart(
                    content=content,
                    blocks=[block],
                    token_count=self._count_tokens(content),
                )
            )
            if start + self.max_tokens >= len(words):
                break
        return parts

    def _overlap_blocks(self, blocks: list[PageBlock]) -> list[PageBlock]:
        selected: list[PageBlock] = []
        count = 0
        for block in reversed(blocks):
            selected.insert(0, block)
            count += self._count_tokens(block.text)
            if count >= self.overlap_tokens:
                break
        return selected

    def _one_part(self, blocks: list[PageBlock]) -> ChunkPart:
        content = self._join(blocks)
        return ChunkPart(
            content=content, blocks=list(blocks), token_count=self._count_tokens(content)
        )

    @staticmethod
    def _blocks_for_section(
        section: DocumentSection,
        ordered_blocks: list[PageBlock],
        positions: dict[str, int],
    ) -> list[PageBlock]:
        start = positions.get(section.start_block_id)
        end = positions.get(section.end_block_id)
        if start is None or end is None or end < start:
            return []
        return ordered_blocks[start : end + 1]

    @staticmethod
    def _heading_metadata(section: DocumentSection | None) -> dict[str, str | None]:
        result: dict[str, str | None] = {
            "chapter": None,
            "section": None,
            "article": None,
            "clause": None,
            "point": None,
            "appendix": None,
            "form_code": None,
        }
        if section is None:
            return result
        for item in section.heading_path:
            section_type = item.get("sectionType")
            label = item.get("label")
            if section_type == SectionType.CHAPTER.value:
                result["chapter"] = label
            elif section_type == SectionType.SECTION.value:
                result["section"] = label
            elif section_type == SectionType.ARTICLE.value:
                result["article"] = label
            elif section_type == SectionType.CLAUSE.value:
                result["clause"] = label
            elif section_type == SectionType.POINT.value:
                result["point"] = label
            elif section_type == SectionType.APPENDIX.value:
                result["appendix"] = label
            elif section_type == SectionType.FORM.value:
                result["form_code"] = label
        return result

    @staticmethod
    def _chunk_type(section: DocumentSection | None) -> str:
        if section is None:
            return "PARAGRAPH"
        if section.section_type in {
            SectionType.ARTICLE,
            SectionType.CLAUSE,
            SectionType.POINT,
            SectionType.SUBPOINT,
        }:
            return "LEGAL_CLAUSE"
        return section.section_type.value

    @staticmethod
    def _printed_page(pages: dict[int, DocumentPage], page_index: int) -> int | None:
        page = pages.get(page_index)
        return page.printed_page_number if page else None

    @staticmethod
    def _table_text(table: DocumentTable) -> str:
        lines: list[str] = []
        if table.title:
            lines.append(table.title)
        lines.extend(" | ".join(row) for row in table.header_rows)
        lines.extend(" | ".join(row) for row in table.rows)
        return "\n".join(lines)

    @staticmethod
    def _join(blocks: list[PageBlock]) -> str:
        return "\n".join(block.text.strip() for block in blocks if block.text.strip())

    @staticmethod
    def _normalize(content: str) -> str:
        return re.sub(r"[ \t]+", " ", unicodedata.normalize("NFC", content)).strip()

    @staticmethod
    def _count_tokens(content: str) -> int:
        return len(re.findall(r"\w+|[^\w\s]", content, flags=re.UNICODE))

from uuid import uuid4

from app.chunking.service import LegalChunker
from app.model.extraction import DocumentPage, PageBlock
from app.model.structure import SectionType
from app.structure.parser import LegalStructureParser


def _models(lines_by_page: list[list[str]]) -> tuple[list[DocumentPage], list[PageBlock]]:
    document_id = str(uuid4())
    pages: list[DocumentPage] = []
    blocks: list[PageBlock] = []
    for page_index, lines in enumerate(lines_by_page):
        page = DocumentPage(
            id=str(uuid4()),
            document_id=document_id,
            page_index=page_index,
            printed_page_number=page_index + 1,
            width=1000,
            height=1400,
            rotation=0,
            has_text_layer=True,
            image_only=False,
            needs_ocr=False,
            extracted_text="\n".join(lines),
        )
        pages.append(page)
        for order_index, text in enumerate(lines):
            block = PageBlock(
                id=str(uuid4()),
                document_id=document_id,
                page=page,
                order_index=order_index,
                text=text,
                normalized_text=text,
                bbox={"x1": 10, "y1": 20, "x2": 900, "y2": 60},
                confidence=0.96,
                source="OCR",
            )
            blocks.append(block)
    return pages, blocks


def test_parser_detects_chapter_article_clause_and_point_hierarchy() -> None:
    pages, blocks = _models(
        [["CHƯƠNG II", "MỤC 1", "Điều 7. Nội dung", "1. Quy định", "a) Trường hợp A"]]
    )

    sections = LegalStructureParser().parse(blocks[0].document_id, blocks)
    by_type = {section.section_type: section for section in sections}

    assert by_type[SectionType.CHAPTER].label == "Chương II"
    assert by_type[SectionType.ARTICLE].label == "Điều 7"
    assert by_type[SectionType.CLAUSE].parent_id == by_type[SectionType.ARTICLE].id
    assert by_type[SectionType.POINT].parent_id == by_type[SectionType.CLAUSE].id


def test_parser_keeps_article_across_page_boundary() -> None:
    _, blocks = _models(
        [
            ["Điều 7. Nội dung", "1. Dòng đầu của khoản"],
            ["Nội dung tiếp tục ở trang sau", "a) Điểm a"],
        ]
    )

    sections = LegalStructureParser().parse(blocks[0].document_id, blocks)
    articles = [section for section in sections if section.section_type == SectionType.ARTICLE]

    assert len(articles) == 1
    assert articles[0].page_start == 0
    assert articles[0].page_end == 1


def test_chunk_preserves_legal_metadata_and_source_anchors() -> None:
    pages, blocks = _models(
        [
            [
                "CHƯƠNG II",
                "MỤC 1",
                "Điều 7. Thời hạn thực hiện",
                "1. Thời hạn là 10 ngày kể từ ngày nhận hồ sơ.",
                "a) Cơ quan phải giữ nguyên số liệu 25 kg.",
            ]
        ]
    )
    sections = LegalStructureParser().parse(blocks[0].document_id, blocks)

    chunks = LegalChunker(min_tokens=10, max_tokens=800, overlap_tokens=5).build(
        blocks[0].document_id,
        pages=pages,
        blocks=blocks,
        sections=sections,
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_type == "LEGAL_CLAUSE"
    assert chunk.chapter == "Chương II"
    assert chunk.section == "Mục 1"
    assert chunk.article == "Điều 7"
    assert chunk.pdf_page_start == 0 == chunk.pdf_page_end
    assert chunk.start_block_id == blocks[2].id
    assert chunk.end_block_id == blocks[-1].id
    assert "10 ngày" in chunk.content
    assert "25 kg" in chunk.content
    assert chunk.bounding_boxes[0]["bbox"]["x1"] == 10

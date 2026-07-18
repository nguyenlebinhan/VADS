from __future__ import annotations

from collections.abc import Iterable

from app.docx_rag.schemas import DocxBlock, DocxChunk


def _split_long_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)
    return [piece for piece in pieces if piece]


def _expanded_blocks(
    blocks: Iterable[DocxBlock], max_chars: int, overlap_chars: int
) -> Iterable[DocxBlock]:
    for block in blocks:
        for piece in _split_long_text(block.text, max_chars, overlap_chars):
            yield block.model_copy(update={"text": piece})


def chunk_blocks(
    blocks: list[DocxBlock],
    *,
    max_chars: int = 1800,
    overlap_chars: int = 250,
) -> list[DocxChunk]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    if not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars must be between 0 and max_chars")

    chunks: list[DocxChunk] = []
    pending: list[DocxBlock] = []
    pending_size = 0
    sequence_by_file: dict[str, int] = {}

    def flush() -> None:
        nonlocal pending, pending_size
        if not pending:
            return
        file_name = pending[0].file_name
        sequence_by_file[file_name] = sequence_by_file.get(file_name, 0) + 1
        sequence = sequence_by_file[file_name]
        paragraphs = sorted(
            {block.paragraph_index for block in pending if block.paragraph_index is not None}
        )
        tables = sorted({block.table_index for block in pending if block.table_index is not None})
        chunks.append(
            DocxChunk(
                chunk_id=f"{file_name}:chunk-{sequence:04d}",
                file_name=file_name,
                text="\n\n".join(block.text for block in pending),
                paragraph_indices=paragraphs,
                table_indices=tables,
                article=next((block.article for block in pending if block.article), None),
                clause=next((block.clause for block in pending if block.clause), None),
                page_number=None,
            )
        )
        pending = []
        pending_size = 0

    for block in _expanded_blocks(blocks, max_chars, overlap_chars):
        if pending:
            first = pending[0]
            metadata_boundary = block.file_name != first.file_name or (
                block.article != first.article or block.clause != first.clause
            )
            size_boundary = pending_size + len(block.text) + 2 > max_chars
            if metadata_boundary or size_boundary:
                flush()
        pending.append(block)
        pending_size += len(block.text) + (2 if len(pending) > 1 else 0)
    flush()
    return chunks

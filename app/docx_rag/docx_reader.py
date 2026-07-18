from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.docx_rag.schemas import BlockKind, DocxBlock, NoDocxFilesError

ARTICLE_RE = re.compile(r"\b(?:Điều|Article)\s+(\d+[A-Za-z]?)\b", re.IGNORECASE)
CLAUSE_RE = re.compile(r"^\s*(?:Khoản\s+)?(\d+)\s*[.)]", re.IGNORECASE)


def find_docx_files(data_dir: Path) -> list[Path]:
    """Return only real .docx files, excluding Word's temporary lock files."""
    files = sorted(
        path
        for path in data_dir.glob("*.docx")
        if path.is_file() and not path.name.startswith("~$")
    )
    if not files:
        raise NoDocxFilesError(f"No DOCX files found in {data_dir.resolve()}")
    return files


def source_signature(files: list[Path]) -> str:
    state = [
        {"name": path.name, "size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}
        for path in files
    ]
    encoded = json.dumps(state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _table_text(table: Table) -> str:
    rows: list[str] = []
    for row in table.rows:
        cells = [" ".join(cell.text.split()) for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows).strip()


def _detect_metadata(text: str) -> tuple[str | None, str | None]:
    article: str | None = None
    clause: str | None = None
    for line in text.splitlines() or [text]:
        article_match = ARTICLE_RE.search(line)
        if article_match:
            article = article_match.group(0).strip().rstrip(".:")
            break
        clause_match = CLAUSE_RE.match(line)
        if clause_match:
            clause = f"Khoản {clause_match.group(1)}"
            break
    return article, clause


def read_docx(path: Path) -> list[DocxBlock]:
    """Read non-empty paragraphs and tables in their document order.

    Paragraph and table indexes are one-based for human-readable citations.
    DOCX has no stable page model, so page_number deliberately remains None.
    """
    document = Document(path)
    blocks: list[DocxBlock] = []
    paragraph_index = 0
    table_index = 0
    current_article: str | None = None
    current_clause: str | None = None

    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            paragraph_index += 1
            text = item.text.strip()
            kind = BlockKind.PARAGRAPH
            item_paragraph_index = paragraph_index
            item_table_index = None
        elif isinstance(item, Table):
            table_index += 1
            text = _table_text(item)
            kind = BlockKind.TABLE
            item_paragraph_index = None
            item_table_index = table_index
        else:  # pragma: no cover - python-docx currently yields only these two types
            continue

        if not text:
            continue

        detected_article, detected_clause = _detect_metadata(text)
        if detected_article:
            current_article = detected_article
            current_clause = None
        if detected_clause:
            current_clause = detected_clause

        blocks.append(
            DocxBlock(
                file_name=path.name,
                kind=kind,
                text=text,
                paragraph_index=item_paragraph_index,
                table_index=item_table_index,
                article=current_article,
                clause=current_clause,
                page_number=None,
            )
        )
    return blocks


def read_docx_directory(data_dir: Path) -> tuple[list[DocxBlock], list[Path]]:
    files = find_docx_files(data_dir)
    blocks: list[DocxBlock] = []
    for path in files:
        blocks.extend(read_docx(path))
    return blocks, files

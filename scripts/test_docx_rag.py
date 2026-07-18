from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.docx_rag.schemas import DocxRagError  # noqa: E402
from app.docx_rag.service import DocxRagService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a DOCX-only RAG index from app/data and ask OpenAI a question."
    )
    parser.add_argument("question", help="Question to answer from the DOCX files")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument(
        "--lexical-only",
        action="store_true",
        help="Skip document embeddings; OpenAI is still used to generate the final answer",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    service = DocxRagService(REPOSITORY_ROOT / "app" / "data")
    try:
        index = service.build_index(
            force_rebuild=True,
            use_embeddings=not args.lexical_only,
        )
        result = service.answer(args.question, top_k=args.top_k)
    except (DocxRagError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(f"Indexed {len(index.chunks)} chunks from app/data")
    print(f"Retrieval: {result.retrieval_mode}")
    if result.embedding_error:
        print(f"Embedding warning: {result.embedding_error}")
    print("\nAnswer:")
    print(result.answer)
    print("\nSources:")
    for number, source in enumerate(result.sources, start=1):
        print(f"{number}. file: {source.file_name}")
        print(f"   chunk_id: {source.chunk_id}")
        print(f"   paragraph: {source.paragraph_index}")
        print(f"   table: {source.table_index}")
        print(f"   article: {source.article}")
        print(f"   clause: {source.clause}")
        print("   page: null")
        print(f'   quote: "{source.quote}"')
    print(f"\nPage note: {result.page_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from app.chat.schemas import AnswerCitation
from app.reranking.contracts import RerankedHit


class ChunkCitationResolver:
    """Navigation adapter derived from indexed Owner-1 chunk anchors."""

    def resolve(self, items: list[RerankedHit]) -> list[AnswerCitation]:
        citations: list[AnswerCitation] = []
        for item in items:
            hit = item.hit
            quote = hit.content.strip()[:300]
            if not quote:
                continue
            citations.append(
                AnswerCitation(
                    document_id=hit.document_id,
                    chunk_id=hit.chunk_id,
                    pdf_page_index=hit.pdf_page_start,
                    printed_page_number=hit.printed_page_start,
                    article=hit.article,
                    clause=hit.clause,
                    point=hit.point,
                    quote=quote,
                    bounding_boxes=list(hit.entity_metadata.get("boundingBoxes") or []),
                )
            )
        return citations

    @staticmethod
    def validate(citations: list[AnswerCitation], items: list[RerankedHit]) -> list[AnswerCitation]:
        content_by_chunk = {item.hit.chunk_id: item.hit.content for item in items}
        return [
            citation
            for citation in citations
            if citation.chunk_id in content_by_chunk
            and citation.quote in content_by_chunk[citation.chunk_id]
        ]

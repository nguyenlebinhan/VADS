import re

from app.chat.schemas import SourceConflict
from app.reranking.contracts import RerankedHit


class SourceValidator:
    _quantified = re.compile(
        r"\b\d[\d.,]*\s*(?:ngày|tháng|năm|đồng|triệu|tỷ|%|kg|km)\b",
        re.IGNORECASE,
    )

    def detect_conflicts(self, question: str, items: list[RerankedHit]) -> list[SourceConflict]:
        if len({item.hit.document_id for item in items}) < 2:
            return []
        if "so sánh" in question.casefold():
            return []
        values: dict[str, set[str]] = {}
        chunk_ids: dict[str, list[str]] = {}
        for item in items:
            topic = (item.hit.article or item.hit.chapter or "Nội dung liên quan").casefold()
            found = {match.group(0) for match in self._quantified.finditer(item.hit.content)}
            if found:
                values.setdefault(topic, set()).update(found)
                chunk_ids.setdefault(topic, []).append(item.hit.chunk_id)
        conflicts: list[SourceConflict] = []
        for topic, topic_values in values.items():
            if len(topic_values) > 1:
                conflicts.append(
                    SourceConflict(
                        topic=topic,
                        values=sorted(topic_values),
                        chunk_ids=chunk_ids[topic],
                        description="Các tài liệu đưa ra giá trị khác nhau cho cùng nội dung.",
                    )
                )
        return conflicts

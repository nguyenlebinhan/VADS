from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.regulatory_change.models import ChangeType, RegulatoryDocumentVersion, RegulatorySection


@dataclass(frozen=True, slots=True)
class ExtractedFact:
    key: str
    value: str
    location: str
    quote: str


@dataclass(frozen=True, slots=True)
class DiffResult:
    change_type: ChangeType
    status: str | None
    fact_key: str
    old_value: str | None
    new_value: str | None
    effective_year: int | None
    old_location: str | None
    new_location: str | None
    summary: str
    confidence: float
    evidence: list[dict[str, Any]]


class SemanticDiffAgent:
    _patterns = {
        "approval_threshold": re.compile(
            r"ngưỡng\s+phê\s+duyệt\s*[:\-]?\s*"
            r"(?P<value>\d+(?:[.,]\d+)?\s*(?:triệu|tỷ)\s*đồng)",
            re.IGNORECASE,
        ),
        "reporting_deadline": re.compile(
            r"thời\s+hạn\s+báo\s+cáo\s*[:\-]?\s*"
            r"(?P<value>\d+\s*(?:ngày|tháng|năm))",
            re.IGNORECASE,
        ),
        "approving_authority": re.compile(
            r"(?:đơn\s+vị|cơ\s+quan)\s+phê\s+duyệt\s*[:\-]?\s*"
            r"(?P<value>[^\n.;]+)",
            re.IGNORECASE,
        ),
    }

    _change_types = {
        "approval_threshold": ChangeType.VALUE_CHANGED,
        "reporting_deadline": ChangeType.DEADLINE_CHANGED,
        "approving_authority": ChangeType.RESPONSIBILITY_CHANGED,
    }

    _labels = {
        "approval_threshold": "Ngưỡng phê duyệt",
        "reporting_deadline": "Thời hạn báo cáo",
        "approving_authority": "Đơn vị phê duyệt",
    }

    def compare(
        self,
        old_version: RegulatoryDocumentVersion,
        new_version: RegulatoryDocumentVersion,
        old_sections: list[RegulatorySection],
        new_sections: list[RegulatorySection],
    ) -> list[DiffResult]:
        old_facts = self._extract(old_version, old_sections)
        new_facts = self._extract(new_version, new_sections)
        results: list[DiffResult] = []
        for key in sorted(set(old_facts) | set(new_facts)):
            old = old_facts.get(key)
            new = new_facts.get(key)
            label = self._labels[key]
            if old and new and self._same_value(old.value, new.value):
                change_type = ChangeType.UNCHANGED
                status = "KEEP_CURRENT_VALUE"
                summary = f"{label} giữ nguyên ở mức {new.value}"
                effective_year = None
            elif old and new:
                change_type = self._change_types[key]
                status = None
                summary = f"{label} thay đổi từ {old.value} thành {new.value}"
                effective_year = new_version.effective_date.year
            elif new:
                change_type = ChangeType.ADDED
                status = None
                summary = f"Bổ sung {label.lower()}: {new.value}"
                effective_year = new_version.effective_date.year
            else:
                change_type = ChangeType.REMOVED
                status = None
                summary = f"Bãi bỏ {label.lower()}: {old.value if old else ''}"
                effective_year = new_version.effective_date.year
            evidence = []
            if old:
                evidence.append(self._evidence(old_version, old, "OLD"))
            if new:
                evidence.append(self._evidence(new_version, new, "NEW"))
            results.append(
                DiffResult(
                    change_type=change_type,
                    status=status,
                    fact_key=key,
                    old_value=old.value if old else None,
                    new_value=new.value if new else None,
                    effective_year=effective_year,
                    old_location=old.location if old else None,
                    new_location=new.location if new else None,
                    summary=summary,
                    confidence=0.99 if old and new else 0.94,
                    evidence=evidence,
                )
            )
        return results

    def extract_current_values(
        self,
        version: RegulatoryDocumentVersion,
        sections: list[RegulatorySection],
    ) -> dict[str, str]:
        return {key: fact.value for key, fact in self._extract(version, sections).items()}

    def _extract(
        self,
        version: RegulatoryDocumentVersion,
        sections: list[RegulatorySection],
    ) -> dict[str, ExtractedFact]:
        facts: dict[str, ExtractedFact] = {}
        for key, pattern in self._patterns.items():
            match = pattern.search(version.raw_text)
            if not match:
                continue
            value = match.group("value").strip()
            quote = match.group(0).strip()
            location = self._find_location(sections, quote, value)
            facts[key] = ExtractedFact(key=key, value=value, location=location, quote=quote)
        return facts

    @staticmethod
    def _find_location(sections: list[RegulatorySection], quote: str, value: str) -> str:
        quote_folded = quote.casefold()
        value_folded = value.casefold()
        for section in sections:
            content = section.content.casefold()
            if quote_folded in content or value_folded in content:
                return section.legal_location
        return "Toàn văn"

    @staticmethod
    def _same_value(old: str, new: str) -> bool:
        def normalize(value: str) -> str:
            return re.sub(r"\s+", " ", value.casefold()).strip()

        return normalize(old) == normalize(new)

    @staticmethod
    def _evidence(
        version: RegulatoryDocumentVersion, fact: ExtractedFact, role: str
    ) -> dict[str, Any]:
        return {
            "sourceRole": role,
            "documentId": version.document_id,
            "documentVersionId": version.id,
            "location": fact.location,
            "quote": fact.quote,
            "value": fact.value,
        }

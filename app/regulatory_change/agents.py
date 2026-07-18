from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.regulatory_change.models import (
    AgentRunStatus,
    ChangeType,
    RegulatoryChange,
    RegulatoryDocumentVersion,
    RegulatoryImpact,
)
from app.regulatory_change.repository import RegulatoryRepository


@dataclass(frozen=True, slots=True)
class VersionResolution:
    previous: RegulatoryDocumentVersion | None
    result: dict[str, Any]
    confidence: float
    evidence: list[dict[str, Any]]


class VersionResolutionAgent:
    def resolve(
        self,
        repository: RegulatoryRepository,
        version: RegulatoryDocumentVersion,
    ) -> VersionResolution:
        previous = repository.previous_version(version)
        return VersionResolution(
            previous=previous,
            result={
                "familyId": version.family_id,
                "currentVersion": version.version_number,
                "previousVersionId": previous.id if previous else None,
                "status": "RESOLVED" if previous else "PREVIOUS_VERSION_NOT_FOUND",
            },
            confidence=1.0 if previous else 0.0,
            evidence=(
                [
                    {
                        "currentDocumentId": version.document_id,
                        "previousDocumentId": previous.document_id,
                        "familyId": version.family_id,
                    }
                ]
                if previous
                else []
            ),
        )


class LegalResearchAgent:
    _reference_pattern = re.compile(
        r"\b(?:Luật|Nghị định|Thông tư|Quyết định)\s+"
        r"(?:số\s+)?[\w./-]+(?:\s*/\s*[A-ZĐ-]+)?",
        re.IGNORECASE,
    )

    def research(
        self, version: RegulatoryDocumentVersion
    ) -> tuple[dict[str, Any], float, list[dict[str, Any]]]:
        references = list(
            dict.fromkeys(
                match.group(0).strip()
                for match in self._reference_pattern.finditer(version.raw_text)
            )
        )
        evidence = [
            {
                "documentId": version.document_id,
                "location": "Toàn văn",
                "quote": reference,
            }
            for reference in references
        ]
        return (
            {
                "references": references,
                "researchStatus": "EXTRACTED_NOT_EXTERNALLY_VERIFIED",
            },
            0.65 if references else 1.0,
            evidence,
        )


class KnowledgeGraphAgent:
    def build(
        self,
        version: RegulatoryDocumentVersion,
        changes: list[RegulatoryChange],
    ) -> tuple[dict[str, Any], float, list[dict[str, Any]]]:
        return (
            {
                "nodes": [
                    {"type": "DOCUMENT_VERSION", "id": version.id},
                    *[{"type": "CHANGE", "id": change.id} for change in changes],
                ],
                "edges": [
                    {
                        "source": version.id,
                        "target": change.id,
                        "type": "HAS_CHANGE",
                    }
                    for change in changes
                ],
            },
            1.0,
            [{"changeId": change.id, "evidence": change.evidence} for change in changes],
        )


@dataclass(frozen=True, slots=True)
class VerificationDecision:
    status: AgentRunStatus
    confidence: float
    issues: list[str]
    checked_claims: int
    rejected_claims: int


class VerificationAgent:
    def verify(
        self,
        previous: RegulatoryDocumentVersion | None,
        changes: list[RegulatoryChange],
        impacts: list[RegulatoryImpact],
    ) -> VerificationDecision:
        issues: list[str] = []
        rejected = 0
        if previous is None:
            issues.append("Không xác định được phiên bản trước; chưa thể kết luận thay đổi.")
        for change in changes:
            required = 2 if change.change_type not in {ChangeType.ADDED, ChangeType.REMOVED} else 1
            if len(change.evidence) < required:
                rejected += 1
                issues.append(f"Thay đổi {change.id} thiếu bằng chứng từ hai phiên bản.")
        for impact in impacts:
            source_types = {item.get("sourceType") for item in impact.evidence}
            if not {"REGULATION", "PROJECT"}.issubset(source_types):
                rejected += 1
                issues.append(f"Tác động {impact.id} thiếu bằng chứng hai phía.")
        checked = len(changes) + len(impacts)
        status = (
            AgentRunStatus.COMPLETED
            if not issues and rejected == 0
            else AgentRunStatus.NEEDS_HUMAN_REVIEW
        )
        confidence = (
            1.0 if checked == 0 and not issues else max(0.0, 1 - rejected / max(checked, 1))
        )
        if previous is None:
            confidence = 0.0
        return VerificationDecision(
            status=status,
            confidence=confidence,
            issues=issues,
            checked_claims=checked,
            rejected_claims=rejected,
        )

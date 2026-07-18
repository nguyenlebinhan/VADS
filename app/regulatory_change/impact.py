from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.regulatory_change.models import (
    ChangeType,
    ImpactLevel,
    RegulatoryChange,
    RegulatoryDocumentVersion,
    RegulatoryProject,
)


@dataclass(frozen=True, slots=True)
class ImpactResult:
    level: ImpactLevel
    confidence: float
    reason: str
    affected_areas: list[dict[str, Any]]
    departments: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    signals: dict[str, float]


class ImpactAnalysisAgent:
    def analyze(
        self,
        version: RegulatoryDocumentVersion,
        changes: list[RegulatoryChange],
        project: RegulatoryProject,
    ) -> ImpactResult | None:
        material_changes = [
            change for change in changes if change.change_type != ChangeType.UNCHANGED
        ]
        if not material_changes:
            return None

        normalized_budgets = " ".join(project.budget_sources)
        normalized_status = self._normalize(project.status)
        normalized_departments = self._normalize(
            " ".join([project.lead_department, *project.coordinating_departments])
        )
        has_value_change = any(
            change.change_type == ChangeType.VALUE_CHANGED for change in material_changes
        )
        has_responsibility_change = any(
            change.change_type == ChangeType.RESPONSIBILITY_CHANGED for change in material_changes
        )
        signals = {
            "domainMatch": 0.15
            if self._normalize(version.domain) == self._normalize(project.domain)
            else 0.0,
            "budgetSourceMatch": 0.25
            if has_value_change and "ngan sach" in self._normalize(normalized_budgets)
            else 0.0,
            "projectStageMatch": 0.20
            if any(token in normalized_status for token in ("cho tham dinh", "in progress"))
            else 0.0,
            "departmentResponsibilityMatch": 0.20
            if has_responsibility_change
            and any(token in normalized_departments for token in ("tai chinh", "ke hoach"))
            else 0.0,
            "legalReferenceMatch": 0.10
            if any(
                self._normalize(version.document_number) in self._normalize(reference)
                for reference in project.legal_bases
            )
            else 0.0,
            "effectiveDateMatch": 0.10,
        }
        score = round(min(1.0, sum(signals.values())), 2)
        if score < 0.20:
            return None
        level = self._level(score)
        project_section = self._project_section(project)
        affected_areas = [
            {
                "projectSection": project_section,
                "documentClause": change.new_location,
                "impactType": change.change_type.value,
                "reason": self._change_reason(change),
                "recommendedAction": self._change_action(change),
                "changeId": change.id,
            }
            for change in material_changes
        ]
        departments = self._departments(project, has_value_change, has_responsibility_change)
        actions = DepartmentAdvisorAgent().recommend(departments, material_changes)
        evidence = [
            {
                "sourceType": "REGULATION",
                "sourceId": change.id,
                "location": change.new_location or "Toàn văn",
                "quote": change.evidence[-1]["quote"] if change.evidence else change.summary,
            }
            for change in material_changes
        ]
        evidence.append(
            {
                "sourceType": "PROJECT",
                "sourceId": project.id,
                "location": project_section,
                "quote": (
                    f"Trạng thái: {project.status}; nguồn vốn: "
                    f"{', '.join(project.budget_sources)}; chủ trì: {project.lead_department}"
                ),
            }
        )
        reason = (
            f"{project.name} sử dụng {', '.join(project.budget_sources) or 'nguồn lực dự án'} "
            f"và đang ở trạng thái {project.status}. Văn bản mới thay đổi "
            "ngưỡng hoặc trách nhiệm phê duyệt liên quan đến hồ sơ dự án."
        )
        return ImpactResult(
            level=level,
            confidence=score,
            reason=reason,
            affected_areas=affected_areas,
            departments=departments,
            actions=actions,
            evidence=evidence,
            signals=signals,
        )

    @staticmethod
    def _level(score: float) -> ImpactLevel:
        if score >= 0.95:
            return ImpactLevel.CRITICAL
        if score >= 0.70:
            return ImpactLevel.HIGH
        if score >= 0.45:
            return ImpactLevel.MEDIUM
        return ImpactLevel.LOW

    @staticmethod
    def _project_section(project: RegulatoryProject) -> str:
        if project.sections:
            first = project.sections[0]
            return str(first.get("title") or first.get("name") or "Thông tin đề án")
        return "Thông tin đề án"

    @staticmethod
    def _change_reason(change: RegulatoryChange) -> str:
        reasons = {
            ChangeType.VALUE_CHANGED: "Ngưỡng ngân sách của hồ sơ có thể không còn phù hợp.",
            ChangeType.RESPONSIBILITY_CHANGED: "Đơn vị có thẩm quyền phê duyệt đã thay đổi.",
            ChangeType.DEADLINE_CHANGED: "Tiến độ hiện tại có thể không đáp ứng thời hạn mới.",
        }
        return reasons.get(change.change_type, change.summary)

    @staticmethod
    def _change_action(change: RegulatoryChange) -> str:
        actions = {
            ChangeType.VALUE_CHANGED: "Kiểm tra ngưỡng ngân sách mới trong hồ sơ trình duyệt.",
            ChangeType.RESPONSIBILITY_CHANGED: "Cập nhật đơn vị nhận và phê duyệt hồ sơ.",
            ChangeType.DEADLINE_CHANGED: "Điều chỉnh mốc tiến độ và lịch báo cáo.",
        }
        return actions.get(change.change_type, "Rà soát nội dung đề án liên quan.")

    @staticmethod
    def _departments(
        project: RegulatoryProject,
        has_value_change: bool,
        has_responsibility_change: bool,
    ) -> list[dict[str, Any]]:
        names = [project.lead_department, *project.coordinating_departments]
        return [
            {
                "department": name,
                "reason": (
                    "Đơn vị chủ trì cần cập nhật hồ sơ và quy trình."
                    if name == project.lead_department
                    else "Đơn vị phối hợp cần rà soát nguồn vốn và thẩm quyền."
                ),
                "matchedSignals": [
                    signal
                    for signal, matched in (
                        ("VALUE_CHANGED", has_value_change),
                        ("RESPONSIBILITY_CHANGED", has_responsibility_change),
                    )
                    if matched
                ],
            }
            for name in dict.fromkeys(names)
        ]

    @staticmethod
    def _normalize(value: str) -> str:
        value = value.replace("Đ", "D").replace("đ", "d")
        normalized = unicodedata.normalize("NFD", value)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return re.sub(r"[^a-z0-9]+", " ", normalized.casefold()).strip()


class DepartmentAdvisorAgent:
    def recommend(
        self,
        departments: list[dict[str, Any]],
        changes: list[RegulatoryChange],
    ) -> list[dict[str, Any]]:
        has_value = any(change.change_type == ChangeType.VALUE_CHANGED for change in changes)
        has_responsibility = any(
            change.change_type == ChangeType.RESPONSIBILITY_CHANGED for change in changes
        )
        actions: list[dict[str, Any]] = []
        for department in departments:
            name = department["department"]
            normalized = ImpactAnalysisAgent._normalize(name)
            if "ke hoach" in normalized:
                department_actions = [
                    "Rà soát lại hồ sơ trình duyệt.",
                    "Cập nhật quy trình và đơn vị nhận hồ sơ."
                    if has_responsibility
                    else "Rà soát tiến độ thực hiện.",
                ]
            elif "tai chinh" in normalized:
                department_actions = [
                    "Kiểm tra ngưỡng ngân sách mới." if has_value else "Rà soát nguồn vốn.",
                    "Cập nhật đơn vị có thẩm quyền phê duyệt."
                    if has_responsibility
                    else "Kiểm tra biểu mẫu tài chính.",
                ]
            else:
                department_actions = ["Rà soát phần việc thuộc trách nhiệm của đơn vị."]
            actions.extend(
                {
                    "department": name,
                    "action": action,
                    "priority": "HIGH",
                    "deadline": None,
                    "evidenceChangeIds": [change.id for change in changes],
                }
                for action in department_actions
            )
        return actions

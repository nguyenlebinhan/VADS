from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from app.citations.schemas import CitationDraft
from app.knowledge_graph.schemas import EdgeType, GraphImportance, NodeType
from app.red_flags.schemas import RedFlagDraft, RedFlagRule, RedFlagSeverity


def _value(item: Any, name: str, default: Any = None) -> Any:
    return getattr(item, name, default)


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _citations(*elements: Any) -> list[CitationDraft]:
    seen: set[tuple[str, str, str, int]] = set()
    result: list[CitationDraft] = []
    for element in elements:
        for raw in _value(element, "citations", []) or []:
            citation = CitationDraft.model_validate(raw)
            key = (citation.document_id, citation.chunk_id, citation.quote, citation.page)
            if key not in seen:
                seen.add(key)
                result.append(citation)
    return result


class RedFlagRuleEngine:
    """Deterministic first-pass checks; it never calls a model."""

    def __init__(self, *, critical_confidence_threshold: float = 0.75) -> None:
        self.critical_confidence_threshold = critical_confidence_threshold

    def evaluate(self, graph: Any) -> list[RedFlagDraft]:
        return self.evaluate_nodes_edges(graph.nodes, graph.edges)

    def evaluate_nodes_edges(
        self,
        nodes: Iterable[Any],
        edges: Iterable[Any],
    ) -> list[RedFlagDraft]:
        node_list = list(nodes)
        edge_list = list(edges)
        by_id = {_value(node, "id", _value(node, "node_id")): node for node in node_list}
        incoming: dict[tuple[str, str], list[Any]] = defaultdict(list)
        outgoing: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for edge in edge_list:
            edge_type = _enum_value(_value(edge, "type"))
            source = _value(edge, "source_node_id")
            target = _value(edge, "target_node_id")
            outgoing[(source, edge_type)].append(edge)
            incoming[(target, edge_type)].append(edge)

        flags: list[RedFlagDraft] = []
        task_types = {NodeType.TASK.value, NodeType.RESPONSIBILITY.value}
        for node in node_list:
            node_id = _value(node, "id", _value(node, "node_id"))
            node_type = _enum_value(_value(node, "type"))
            name = _value(node, "canonical_name", None) or _value(node, "name", node_id)
            if (
                node_type in task_types
                and not incoming[(node_id, EdgeType.ASSIGNS_RESPONSIBILITY.value)]
            ):
                flags.append(
                    self._flag(
                        RedFlagRule.MISSING_RESPONSIBLE_ACTOR,
                        RedFlagSeverity.HIGH,
                        f"Chưa xác định chủ thể chịu trách nhiệm: {name}",
                        "Nhiệm vụ/trách nhiệm không có quan hệ ASSIGNS_RESPONSIBILITY từ chủ thể.",
                        nodes=[node],
                    )
                )
            if (
                node_type in {NodeType.TASK.value, NodeType.PROCEDURE.value}
                and not incoming[(node_id, EdgeType.LEADS.value)]
            ):
                flags.append(
                    self._flag(
                        RedFlagRule.MISSING_LEAD_AGENCY,
                        RedFlagSeverity.HIGH,
                        f"Chưa có cơ quan chủ trì: {name}",
                        "Nhiệm vụ/thủ tục không có quan hệ LEADS từ cơ quan chủ trì.",
                        nodes=[node],
                    )
                )
            if (
                node_type == NodeType.TASK.value
                and not outgoing[(node_id, EdgeType.HAS_DEADLINE.value)]
            ):
                flags.append(
                    self._flag(
                        RedFlagRule.MISSING_DEADLINE,
                        RedFlagSeverity.MEDIUM,
                        f"Nhiệm vụ chưa có thời hạn: {name}",
                        "Không tìm thấy quan hệ HAS_DEADLINE cho nhiệm vụ.",
                        nodes=[node],
                    )
                )
            if (
                node_type == NodeType.DOSSIER.value
                and not outgoing[(node_id, EdgeType.SUBMITS.value)]
            ):
                flags.append(
                    self._flag(
                        RedFlagRule.DOSSIER_WITHOUT_RECEIVING_AUTHORITY,
                        RedFlagSeverity.HIGH,
                        f"Hồ sơ chưa có cơ quan tiếp nhận: {name}",
                        "Hồ sơ không có quan hệ SUBMITS tới cơ quan/thẩm quyền tiếp nhận.",
                        nodes=[node],
                    )
                )
            if node_type == NodeType.BUDGET.value:
                properties = _value(node, "properties", {}) or {}
                amount = next(
                    (properties.get(key) for key in ("amount", "budgetAmount", "value")),
                    None,
                )
                if amount in (None, ""):
                    flags.append(
                        self._flag(
                            RedFlagRule.MISSING_BUDGET_AMOUNT,
                            RedFlagSeverity.MEDIUM,
                            f"Ngân sách chưa có số tiền: {name}",
                            "Node BUDGET không có amount/budgetAmount/value.",
                            nodes=[node],
                        )
                    )
                funding_edges = (
                    outgoing[(node_id, EdgeType.HAS_FUNDING_SOURCE.value)]
                    + incoming[(node_id, EdgeType.HAS_FUNDING_SOURCE.value)]
                )
                if not funding_edges:
                    flags.append(
                        self._flag(
                            RedFlagRule.MISSING_FUNDING_SOURCE,
                            RedFlagSeverity.HIGH,
                            f"Ngân sách chưa có nguồn kinh phí: {name}",
                            "Không tìm thấy quan hệ HAS_FUNDING_SOURCE cho ngân sách.",
                            nodes=[node],
                        )
                    )
            if node_type == NodeType.LEGAL_REFERENCE.value:
                properties = _value(node, "properties", {}) or {}
                reference_edges = (
                    outgoing[(node_id, EdgeType.REFERENCES.value)]
                    + incoming[(node_id, EdgeType.REFERENCES.value)]
                )
                if properties.get("resolved") is False or not reference_edges:
                    flags.append(
                        self._flag(
                            RedFlagRule.BROKEN_LEGAL_REFERENCE,
                            RedFlagSeverity.MEDIUM,
                            f"Tham chiếu pháp lý không phân giải được: {name}",
                            "LEGAL_REFERENCE chưa được nối bằng REFERENCES hoặc resolved=false.",
                            nodes=[node],
                        )
                    )
                if properties.get("targetType") == "FORM" and properties.get("resolved") is False:
                    flags.append(
                        self._flag(
                            RedFlagRule.MISSING_REFERENCED_FORM,
                            RedFlagSeverity.MEDIUM,
                            f"Thiếu biểu mẫu được viện dẫn: {name}",
                            "Tham chiếu tới FORM chưa được phân giải.",
                            nodes=[node],
                        )
                    )
            if (
                _enum_value(_value(node, "importance", GraphImportance.MEDIUM))
                == GraphImportance.CRITICAL.value
                and float(_value(node, "confidence", 1.0)) < self.critical_confidence_threshold
            ):
                flags.append(
                    self._flag(
                        RedFlagRule.LOW_CONFIDENCE_CRITICAL_TEXT,
                        RedFlagSeverity.CRITICAL,
                        f"Nội dung trọng yếu có confidence thấp: {name}",
                        "Node CRITICAL có confidence dưới ngưỡng kiểm tra.",
                        nodes=[node],
                    )
                )

        for (target_id, edge_type), grouped in incoming.items():
            target = by_id.get(target_id)
            if edge_type == EdgeType.LEADS.value and len(grouped) > 1:
                flags.append(
                    self._flag(
                        RedFlagRule.MULTIPLE_LEAD_AGENCIES,
                        RedFlagSeverity.HIGH,
                        "Có nhiều cơ quan cùng được giao chủ trì",
                        "Một nhiệm vụ/thủ tục nhận nhiều hơn một quan hệ LEADS.",
                        nodes=[target] if target else [],
                        edges=grouped,
                    )
                )
            if edge_type == EdgeType.ASSIGNS_RESPONSIBILITY.value and len(grouped) > 1:
                flags.append(
                    self._flag(
                        RedFlagRule.CONFLICTING_RESPONSIBILITY,
                        RedFlagSeverity.CRITICAL,
                        "Trách nhiệm có dấu hiệu chồng chéo",
                        "Cùng một đối tượng nhận nhiều quan hệ ASSIGNS_RESPONSIBILITY.",
                        nodes=[target] if target else [],
                        edges=grouped,
                    )
                )

        for (source_id, edge_type), grouped in list(outgoing.items()):
            source = by_id.get(source_id)
            if edge_type == EdgeType.HAS_DEADLINE.value:
                if not outgoing[(source_id, EdgeType.PRODUCES.value)]:
                    flags.append(
                        self._flag(
                            RedFlagRule.DEADLINE_WITHOUT_OUTPUT,
                            RedFlagSeverity.HIGH,
                            "Có thời hạn nhưng chưa xác định đầu ra",
                            "Chủ thể có HAS_DEADLINE nhưng không có PRODUCES.",
                            nodes=[source] if source else [],
                            edges=grouped,
                        )
                    )
                if len(grouped) > 1 and self._different_targets(grouped, by_id):
                    flags.append(
                        self._flag(
                            RedFlagRule.CONFLICTING_DEADLINE,
                            RedFlagSeverity.HIGH,
                            "Có nhiều thời hạn không thống nhất",
                            "Một đối tượng có nhiều deadline mang giá trị khác nhau.",
                            nodes=[source] if source else [],
                            edges=grouped,
                        )
                    )
            if edge_type == EdgeType.HAS_BUDGET.value and len(grouped) > 1:
                if self._different_targets(grouped, by_id):
                    flags.append(
                        self._flag(
                            RedFlagRule.CONFLICTING_BUDGET,
                            RedFlagSeverity.CRITICAL,
                            "Có nhiều mức ngân sách không thống nhất",
                            "Một đối tượng có nhiều budget mang giá trị khác nhau.",
                            nodes=[source] if source else [],
                            edges=grouped,
                        )
                    )

        for edge in edge_list:
            if (
                _enum_value(_value(edge, "importance", GraphImportance.MEDIUM))
                == GraphImportance.CRITICAL.value
                and float(_value(edge, "confidence", 1.0)) < self.critical_confidence_threshold
            ):
                flags.append(
                    self._flag(
                        RedFlagRule.LOW_CONFIDENCE_CRITICAL_TEXT,
                        RedFlagSeverity.CRITICAL,
                        "Quan hệ trọng yếu có confidence thấp",
                        "Edge CRITICAL có confidence dưới ngưỡng kiểm tra.",
                        edges=[edge],
                    )
                )
        return self._deduplicate(flags)

    @staticmethod
    def _different_targets(edges: list[Any], by_id: dict[str, Any]) -> bool:
        values = set()
        for edge in edges:
            target_id = _value(edge, "target_node_id")
            target = by_id.get(target_id)
            if target is None:
                values.add(target_id)
                continue
            properties = _value(target, "properties", {}) or {}
            values.add(
                str(
                    properties.get("amount")
                    or properties.get("value")
                    or _value(target, "canonical_name", None)
                    or _value(target, "name", target_id)
                ).casefold()
            )
        return len(values) > 1

    @staticmethod
    def _flag(
        issue_type: RedFlagRule,
        severity: RedFlagSeverity,
        title: str,
        description: str,
        *,
        nodes: list[Any] | None = None,
        edges: list[Any] | None = None,
    ) -> RedFlagDraft:
        nodes = [node for node in (nodes or []) if node is not None]
        edges = edges or []
        return RedFlagDraft(
            issueType=issue_type,
            severity=severity,
            title=title,
            description=description,
            relatedNodeIds=[_value(node, "id", _value(node, "node_id")) for node in nodes],
            relatedEdgeIds=[_value(edge, "id", _value(edge, "edge_id")) for edge in edges],
            citations=_citations(*nodes, *edges),
            evidence={
                "nodeCount": len(nodes),
                "edgeCount": len(edges),
            },
        )

    @staticmethod
    def _deduplicate(flags: list[RedFlagDraft]) -> list[RedFlagDraft]:
        unique: dict[tuple[str, tuple[str, ...], tuple[str, ...]], RedFlagDraft] = {}
        for flag in flags:
            key = (
                flag.issue_type.value,
                tuple(sorted(flag.related_node_ids)),
                tuple(sorted(flag.related_edge_ids)),
            )
            unique.setdefault(key, flag)
        return list(unique.values())

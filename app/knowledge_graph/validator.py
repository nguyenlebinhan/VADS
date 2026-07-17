from __future__ import annotations

from app.citations.validator import CitationValidator
from app.knowledge_graph.schemas import (
    GraphExtractionOutput,
    GraphImportance,
    GraphValidationIssue,
)


class KnowledgeGraphValidator:
    def __init__(self, citation_validator: CitationValidator) -> None:
        self.citation_validator = citation_validator

    def validate(
        self,
        graph: GraphExtractionOutput,
        *,
        document_id: str,
    ) -> list[GraphValidationIssue]:
        issues: list[GraphValidationIssue] = []
        node_ids = {node.node_id for node in graph.nodes}
        for edge in graph.edges:
            if edge.source_node_id not in node_ids:
                issues.append(
                    self._issue("MISSING_SOURCE_NODE", "EDGE", edge.edge_id, edge.source_node_id)
                )
            if edge.target_node_id not in node_ids:
                issues.append(
                    self._issue("MISSING_TARGET_NODE", "EDGE", edge.edge_id, edge.target_node_id)
                )

        for element_type, elements in (("NODE", graph.nodes), ("EDGE", graph.edges)):
            for element in elements:
                if element.importance not in {GraphImportance.HIGH, GraphImportance.CRITICAL}:
                    continue
                if not element.citations:
                    issues.append(
                        self._issue(
                            "IMPORTANT_ELEMENT_REQUIRES_CITATION",
                            element_type,
                            element.node_id if element_type == "NODE" else element.edge_id,
                            "No citation supplied",
                        )
                    )
                    continue
                for result in self.citation_validator.validate_all(
                    element.citations,
                    expected_document_id=document_id,
                ):
                    for citation_issue in result.issues:
                        issues.append(
                            self._issue(
                                f"CITATION_{citation_issue.code}",
                                element_type,
                                element.node_id if element_type == "NODE" else element.edge_id,
                                citation_issue.message,
                            )
                        )
        return issues

    @staticmethod
    def _issue(
        code: str,
        element_type: str,
        element_id: str,
        detail: str,
    ) -> GraphValidationIssue:
        return GraphValidationIssue(
            code=code,
            elementType=element_type,
            elementId=element_id,
            message=detail,
        )

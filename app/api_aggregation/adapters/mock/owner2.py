from typing import Any


class MockSummaryReader:
    def get_latest_summary(self, document_id: str) -> dict[str, Any] | None:
        del document_id
        return None


class MockKnowledgeGraphReader:
    def get_graph_overview(self, document_id: str) -> dict[str, Any]:
        del document_id
        return {"nodes": [], "edges": [], "statistics": {"nodeCount": 0, "edgeCount": 0}}


class MockRedFlagReader:
    def list_red_flags(self, document_id: str) -> list[dict[str, Any]]:
        del document_id
        return []


class MockCriticalQuestionReader:
    def list_critical_questions(self, document_id: str) -> list[dict[str, Any]]:
        del document_id
        return []

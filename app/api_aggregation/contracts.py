from typing import Any, Protocol


class SummaryReader(Protocol):
    def get_latest_summary(self, document_id: str) -> dict[str, Any] | None: ...


class KnowledgeGraphReader(Protocol):
    def get_graph_overview(self, document_id: str) -> dict[str, Any]: ...


class RedFlagReader(Protocol):
    def list_red_flags(self, document_id: str) -> list[dict[str, Any]]: ...


class CriticalQuestionReader(Protocol):
    def list_critical_questions(self, document_id: str) -> list[dict[str, Any]]: ...


class PageImageUrlSigner(Protocol):
    def sign_page_image(self, object_key: str, *, expires_seconds: int = 900) -> str: ...

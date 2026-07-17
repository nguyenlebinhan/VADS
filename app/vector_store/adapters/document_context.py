from dataclasses import dataclass
from typing import Protocol

from app.model.repositories.documents import DocumentRepository


@dataclass(frozen=True, slots=True)
class DocumentContext:
    document_id: str
    workspace_id: str


class DocumentContextReader(Protocol):
    def get_context(self, document_id: str) -> DocumentContext | None: ...


class Owner1DocumentContextAdapter:
    """Adapter around Owner 1's repository; indexing never reads its tables directly."""

    def __init__(self, session) -> None:
        self.repository = DocumentRepository(session)

    def get_context(self, document_id: str) -> DocumentContext | None:
        document = self.repository.get_active(document_id)
        if document is None:
            return None
        return DocumentContext(document_id=document.id, workspace_id=document.workspace_id)

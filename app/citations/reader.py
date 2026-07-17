from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.citations.repository import CitationRepository
from app.citations.schemas import CitationOwnerType, CitationView


class CitationReader(Protocol):
    def list_for_owner(
        self,
        owner_type: CitationOwnerType,
        owner_id: str,
    ) -> list[CitationView]: ...

    def list_for_document(self, document_id: str) -> list[CitationView]: ...


class SqlAlchemyCitationReader:
    def __init__(self, session: Session) -> None:
        self.repository = CitationRepository(session)

    def list_for_owner(
        self,
        owner_type: CitationOwnerType,
        owner_id: str,
    ) -> list[CitationView]:
        return [
            self.repository.view(citation)
            for citation in self.repository.list_for_owner(owner_type, owner_id)
        ]

    def list_for_document(self, document_id: str) -> list[CitationView]:
        return [
            self.repository.view(citation)
            for citation in self.repository.list_for_document(document_id)
        ]

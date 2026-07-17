from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.citations.models import Citation
from app.citations.schemas import CitationOwnerType, CitationValidationResult, CitationView


class CitationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_validated(
        self,
        result: CitationValidationResult,
        *,
        owner_type: CitationOwnerType,
        owner_id: str,
    ) -> Citation:
        if not result.valid or result.normalized_quote is None:
            raise ValueError("Only validated citations may be persisted")
        draft = result.citation
        citation = Citation(
            owner_type=owner_type.value,
            owner_id=owner_id,
            document_id=draft.document_id,
            chunk_id=draft.chunk_id,
            quote=draft.quote,
            normalized_quote=result.normalized_quote,
            page=draft.page,
            bounding_box=(
                draft.bounding_box.model_dump() if draft.bounding_box is not None else None
            ),
            article=draft.article,
            clause=draft.clause,
            point=draft.point,
            source_confidence=draft.source_confidence,
        )
        self.session.add(citation)
        self.session.flush()
        return citation

    def list_for_owner(
        self,
        owner_type: CitationOwnerType,
        owner_id: str,
    ) -> list[Citation]:
        statement = (
            select(Citation)
            .where(Citation.owner_type == owner_type.value, Citation.owner_id == owner_id)
            .order_by(Citation.created_at, Citation.id)
        )
        return list(self.session.scalars(statement))

    def list_for_document(self, document_id: str) -> list[Citation]:
        statement = (
            select(Citation)
            .where(Citation.document_id == document_id)
            .order_by(Citation.created_at, Citation.id)
        )
        return list(self.session.scalars(statement))

    def delete_for_owner(self, owner_type: CitationOwnerType, owner_id: str) -> None:
        self.session.execute(
            delete(Citation).where(
                Citation.owner_type == owner_type.value,
                Citation.owner_id == owner_id,
            )
        )

    @staticmethod
    def view(citation: Citation) -> CitationView:
        return CitationView.model_validate(citation)

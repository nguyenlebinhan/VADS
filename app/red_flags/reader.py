from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.citations.reader import CitationReader, SqlAlchemyCitationReader
from app.citations.schemas import CitationOwnerType
from app.red_flags.models import RedFlag
from app.red_flags.repository import RedFlagRepository
from app.red_flags.schemas import RedFlagView


class RedFlagReader(Protocol):
    def list_for_document(
        self,
        document_id: str,
        *,
        include_suppressed: bool = False,
    ) -> list[RedFlagView]: ...

    def get_red_flag(self, flag_id: str) -> RedFlagView | None: ...


class SqlAlchemyRedFlagReader:
    def __init__(self, session: Session, citation_reader: CitationReader | None = None) -> None:
        self.repository = RedFlagRepository(session)
        self.citation_reader = citation_reader or SqlAlchemyCitationReader(session)

    def list_for_document(
        self,
        document_id: str,
        *,
        include_suppressed: bool = False,
    ) -> list[RedFlagView]:
        return [
            self._view(flag)
            for flag in self.repository.list_for_document(
                document_id,
                include_suppressed=include_suppressed,
            )
        ]

    def get_red_flag(self, flag_id: str) -> RedFlagView | None:
        flag = self.repository.get(flag_id)
        return self._view(flag) if flag else None

    def _view(self, flag: RedFlag) -> RedFlagView:
        return RedFlagView(
            id=flag.id,
            documentId=flag.document_id,
            graphVersionId=flag.graph_version_id,
            issueType=flag.issue_type,
            severity=flag.severity,
            title=flag.title,
            description=flag.description,
            relatedNodeIds=self.repository.list_node_ids(flag.id),
            relatedEdgeIds=flag.related_edge_ids,
            evidence=flag.evidence,
            status=flag.status,
            verificationModel=flag.verification_model,
            verificationReason=flag.verification_reason,
            citations=self.citation_reader.list_for_owner(
                CitationOwnerType.RED_FLAG,
                flag.id,
            ),
            createdAt=flag.created_at,
        )

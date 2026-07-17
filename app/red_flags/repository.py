from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.models import GraphVersion
from app.red_flags.models import CriticalQuestion, RedFlag, RedFlagNode
from app.red_flags.schemas import (
    CriticalQuestionDraft,
    QuestionVerificationStatus,
    RedFlagDraft,
)


class RedFlagRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        document_id: str,
        graph_version_id: str,
        workflow_id: str,
        draft: RedFlagDraft,
    ) -> RedFlag:
        flag = RedFlag(
            document_id=document_id,
            graph_version_id=graph_version_id,
            workflow_id=workflow_id,
            issue_type=draft.issue_type.value,
            severity=draft.severity.value,
            title=draft.title,
            description=draft.description,
            related_edge_ids=draft.related_edge_ids,
            evidence=draft.evidence,
            status=draft.status.value,
            verification_model=draft.verification_model,
            verification_reason=draft.verification_reason,
        )
        self.session.add(flag)
        self.session.flush()
        for node_id in dict.fromkeys(draft.related_node_ids):
            self.session.add(RedFlagNode(red_flag_id=flag.id, node_id=node_id))
        self.session.flush()
        return flag

    def list_for_document(
        self,
        document_id: str,
        *,
        include_suppressed: bool = False,
    ) -> list[RedFlag]:
        statement = (
            select(RedFlag)
            .join(GraphVersion, GraphVersion.id == RedFlag.graph_version_id)
            .where(
                RedFlag.document_id == document_id,
                GraphVersion.is_current.is_(True),
            )
        )
        if not include_suppressed:
            statement = statement.where(RedFlag.status != "SUPPRESSED")
        return list(self.session.scalars(statement.order_by(RedFlag.created_at.desc(), RedFlag.id)))

    def get(self, flag_id: str) -> RedFlag | None:
        return self.session.get(RedFlag, flag_id)

    def list_node_ids(self, flag_id: str) -> list[str]:
        statement = select(RedFlagNode.node_id).where(RedFlagNode.red_flag_id == flag_id)
        return list(self.session.scalars(statement))


class CriticalQuestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        document_id: str,
        workflow_id: str,
        draft: CriticalQuestionDraft,
        verification_status: QuestionVerificationStatus,
        verification_model: str | None,
        red_flag_id: str | None = None,
    ) -> CriticalQuestion:
        question = CriticalQuestion(
            document_id=document_id,
            workflow_id=workflow_id,
            red_flag_id=red_flag_id,
            question=draft.question,
            reason=draft.reason,
            issue_type=draft.issue_type.value,
            severity=draft.severity.value,
            related_subject=draft.related_subject,
            source_location=draft.source_location,
            risk_if_unresolved=draft.risk_if_unresolved,
            verification_status=verification_status.value,
            verification_model=verification_model,
        )
        self.session.add(question)
        self.session.flush()
        return question

    def list_for_document(self, document_id: str) -> list[CriticalQuestion]:
        statement = (
            select(CriticalQuestion)
            .where(
                CriticalQuestion.document_id == document_id,
                CriticalQuestion.verification_status == QuestionVerificationStatus.VERIFIED.value,
            )
            .order_by(CriticalQuestion.created_at.desc(), CriticalQuestion.id)
        )
        return list(self.session.scalars(statement))

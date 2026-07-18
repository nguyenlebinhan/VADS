from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.regulatory_change.models import (
    RegulatoryAgentOutput,
    RegulatoryAgentRun,
    RegulatoryAgentTask,
    RegulatoryChange,
    RegulatoryDocumentFamily,
    RegulatoryDocumentVersion,
    RegulatoryImpact,
    RegulatoryProject,
    RegulatorySection,
    RegulatoryVerificationResult,
)


class RegulatoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def family(self, workspace_id: str, family_key: str) -> RegulatoryDocumentFamily | None:
        return self.session.scalar(
            select(RegulatoryDocumentFamily).where(
                RegulatoryDocumentFamily.workspace_id == workspace_id,
                RegulatoryDocumentFamily.family_key == family_key,
            )
        )

    def version_by_document(self, document_id: str) -> RegulatoryDocumentVersion | None:
        return self.session.scalar(
            select(RegulatoryDocumentVersion).where(
                RegulatoryDocumentVersion.document_id == document_id
            )
        )

    def version(self, version_id: str) -> RegulatoryDocumentVersion | None:
        return self.session.get(RegulatoryDocumentVersion, version_id)

    def versions(self, family_id: str) -> list[RegulatoryDocumentVersion]:
        return list(
            self.session.scalars(
                select(RegulatoryDocumentVersion)
                .where(RegulatoryDocumentVersion.family_id == family_id)
                .order_by(
                    RegulatoryDocumentVersion.effective_date.desc(),
                    RegulatoryDocumentVersion.created_at.desc(),
                )
            )
        )

    def previous_version(
        self, version: RegulatoryDocumentVersion
    ) -> RegulatoryDocumentVersion | None:
        return self.session.scalar(
            select(RegulatoryDocumentVersion)
            .where(
                RegulatoryDocumentVersion.family_id == version.family_id,
                RegulatoryDocumentVersion.effective_date < version.effective_date,
            )
            .order_by(RegulatoryDocumentVersion.effective_date.desc())
            .limit(1)
        )

    def sections(self, version_id: str) -> list[RegulatorySection]:
        return list(
            self.session.scalars(
                select(RegulatorySection)
                .where(RegulatorySection.document_version_id == version_id)
                .order_by(RegulatorySection.order_index)
            )
        )

    def changes(self, version_id: str) -> list[RegulatoryChange]:
        return list(
            self.session.scalars(
                select(RegulatoryChange)
                .where(RegulatoryChange.new_version_id == version_id)
                .order_by(RegulatoryChange.fact_key)
            )
        )

    def clear_changes(self, version_id: str) -> None:
        self.session.execute(
            delete(RegulatoryChange).where(RegulatoryChange.new_version_id == version_id)
        )

    def projects(self, workspace_id: str | None = None) -> list[RegulatoryProject]:
        query = select(RegulatoryProject).order_by(RegulatoryProject.updated_at.desc())
        if workspace_id:
            query = query.where(RegulatoryProject.workspace_id == workspace_id)
        return list(self.session.scalars(query))

    def project(self, project_id: str) -> RegulatoryProject | None:
        return self.session.get(RegulatoryProject, project_id)

    def project_by_code(self, workspace_id: str, project_code: str) -> RegulatoryProject | None:
        return self.session.scalar(
            select(RegulatoryProject).where(
                RegulatoryProject.workspace_id == workspace_id,
                RegulatoryProject.project_code == project_code,
            )
        )

    def impact(self, impact_id: str) -> RegulatoryImpact | None:
        return self.session.get(RegulatoryImpact, impact_id)

    def impacts(
        self,
        *,
        document_version_id: str | None = None,
        project_id: str | None = None,
        department: str | None = None,
    ) -> list[RegulatoryImpact]:
        query = select(RegulatoryImpact).order_by(RegulatoryImpact.created_at.desc())
        if document_version_id:
            query = query.where(RegulatoryImpact.document_version_id == document_version_id)
        if project_id:
            query = query.where(RegulatoryImpact.project_id == project_id)
        impacts = list(self.session.scalars(query))
        if department:
            normalized = department.casefold()
            impacts = [
                impact
                for impact in impacts
                if any(
                    item.get("department", "").casefold() == normalized
                    for item in impact.departments
                )
            ]
        return impacts

    def run(self, run_id: str) -> RegulatoryAgentRun | None:
        return self.session.get(RegulatoryAgentRun, run_id)

    def run_by_key(self, idempotency_key: str) -> RegulatoryAgentRun | None:
        return self.session.scalar(
            select(RegulatoryAgentRun).where(RegulatoryAgentRun.idempotency_key == idempotency_key)
        )

    def tasks(self, run_id: str) -> list[RegulatoryAgentTask]:
        return list(
            self.session.scalars(
                select(RegulatoryAgentTask)
                .where(RegulatoryAgentTask.agent_run_id == run_id)
                .order_by(RegulatoryAgentTask.sequence_number)
            )
        )

    def output(self, task_id: str) -> RegulatoryAgentOutput | None:
        return self.session.scalar(
            select(RegulatoryAgentOutput).where(RegulatoryAgentOutput.agent_task_id == task_id)
        )

    def verification(self, run_id: str) -> RegulatoryVerificationResult | None:
        return self.session.scalar(
            select(RegulatoryVerificationResult).where(
                RegulatoryVerificationResult.agent_run_id == run_id
            )
        )

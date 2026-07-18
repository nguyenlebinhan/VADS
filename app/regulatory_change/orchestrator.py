from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.regulatory_change.agents import (
    KnowledgeGraphAgent,
    LegalResearchAgent,
    VerificationAgent,
    VersionResolutionAgent,
)
from app.regulatory_change.diff import SemanticDiffAgent
from app.regulatory_change.impact import ImpactAnalysisAgent
from app.regulatory_change.models import (
    AgentRunStatus,
    RegulatoryAgentOutput,
    RegulatoryAgentRun,
    RegulatoryAgentTask,
    RegulatoryChange,
    RegulatoryDocumentStatus,
    RegulatoryDocumentVersion,
    RegulatoryImpact,
    RegulatoryVerificationResult,
)
from app.regulatory_change.repository import RegulatoryRepository


class RegulatoryOrchestrator:
    PIPELINE_VERSION = "regulatory-mvp-v1"
    AGENTS = (
        "DocumentIntakeAgent",
        "VersionResolutionAgent",
        "SemanticDiffAgent",
        "LegalResearchAgent",
        "KnowledgeGraphAgent",
        "ImpactAnalysisAgent",
        "DepartmentAdvisorAgent",
        "VerificationAgent",
    )

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = RegulatoryRepository(session)
        self.version_agent = VersionResolutionAgent()
        self.diff_agent = SemanticDiffAgent()
        self.legal_research_agent = LegalResearchAgent()
        self.knowledge_graph_agent = KnowledgeGraphAgent()
        self.impact_agent = ImpactAnalysisAgent()
        self.verification_agent = VerificationAgent()

    def analyze(
        self, version: RegulatoryDocumentVersion, *, force: bool = False
    ) -> RegulatoryAgentRun:
        base_key = f"{version.id}:{self.PIPELINE_VERSION}"
        existing = self.repository.run_by_key(base_key)
        if existing and not force:
            return existing
        attempt = 1
        idempotency_key = base_key
        if existing:
            prior_runs = [
                run
                for run in self.session.query(RegulatoryAgentRun).filter(
                    RegulatoryAgentRun.document_version_id == version.id
                )
            ]
            attempt = max(run.attempt for run in prior_runs) + 1
            idempotency_key = f"{base_key}:attempt-{attempt}"
            self.repository.clear_changes(version.id)

        now = datetime.now(UTC)
        run = RegulatoryAgentRun(
            document_version_id=version.id,
            idempotency_key=idempotency_key,
            status=AgentRunStatus.RUNNING,
            attempt=attempt,
            started_at=now,
        )
        self.session.add(run)
        self.session.flush()
        run_id = run.id
        self.session.commit()
        run = self.repository.run(run_id)
        assert run is not None
        try:
            sections = self.repository.sections(version.id)
            self._task(
                run,
                1,
                self.AGENTS[0],
                [{"documentId": version.document_id}],
                lambda: (
                    {
                        "sectionCount": len(sections),
                        "metadata": {
                            "title": version.title,
                            "documentNumber": version.document_number,
                            "issuingAgency": version.issuing_agency,
                            "issuedDate": version.issued_date.isoformat(),
                            "effectiveDate": version.effective_date.isoformat(),
                            "domain": version.domain,
                        },
                    },
                    1.0,
                    [self._section_evidence(section) for section in sections[:3]],
                ),
            )
            resolution = self.version_agent.resolve(self.repository, version)
            previous = resolution.previous
            self._task(
                run,
                2,
                self.AGENTS[1],
                [{"documentVersionId": version.id}],
                lambda: (resolution.result, resolution.confidence, resolution.evidence),
            )

            changes: list[RegulatoryChange] = []
            if previous:
                diff_results = self.diff_agent.compare(
                    previous,
                    version,
                    self.repository.sections(previous.id),
                    sections,
                )
                changes = [
                    RegulatoryChange(
                        old_version_id=previous.id,
                        new_version_id=version.id,
                        change_type=result.change_type,
                        status=result.status,
                        fact_key=result.fact_key,
                        old_value=result.old_value,
                        new_value=result.new_value,
                        effective_year=result.effective_year,
                        old_location=result.old_location,
                        new_location=result.new_location,
                        summary=result.summary,
                        confidence=result.confidence,
                        evidence=result.evidence,
                    )
                    for result in diff_results
                ]
                self.session.add_all(changes)
                self.session.flush()
            self._task(
                run,
                3,
                self.AGENTS[2],
                [
                    {"documentVersionId": version.id},
                    {"previousVersionId": previous.id if previous else None},
                ],
                lambda: (
                    {
                        "changeCount": len(changes),
                        "changes": [self._change_result(change) for change in changes],
                    },
                    min((change.confidence for change in changes), default=0.0),
                    [evidence for change in changes for evidence in change.evidence],
                ),
            )

            self._task(
                run,
                4,
                self.AGENTS[3],
                [{"documentVersionId": version.id}],
                lambda: self.legal_research_agent.research(version),
            )
            self._task(
                run,
                5,
                self.AGENTS[4],
                [{"documentVersionId": version.id}],
                lambda: self.knowledge_graph_agent.build(version, changes),
            )

            impacts: list[RegulatoryImpact] = []
            for project in self.repository.projects(
                version_document_workspace(version, self.session)
            ):
                result = self.impact_agent.analyze(version, changes, project)
                if result is None:
                    continue
                impact = RegulatoryImpact(
                    document_version_id=version.id,
                    project_id=project.id,
                    agent_run_id=run.id,
                    impact_level=result.level,
                    confidence=result.confidence,
                    reason=result.reason,
                    affected_areas=result.affected_areas,
                    departments=result.departments,
                    recommended_actions=result.actions,
                    evidence=result.evidence,
                    review_status="PENDING",
                )
                self.session.add(impact)
                impacts.append(impact)
            self.session.flush()
            self._task(
                run,
                6,
                self.AGENTS[5],
                [{"changeId": change.id} for change in changes],
                lambda: (
                    {
                        "impactCount": len(impacts),
                        "impacts": [
                            {
                                "impactId": impact.id,
                                "projectId": impact.project_id,
                                "impactLevel": impact.impact_level.value,
                                "confidence": impact.confidence,
                            }
                            for impact in impacts
                        ],
                    },
                    min((impact.confidence for impact in impacts), default=0.0),
                    [evidence for impact in impacts for evidence in impact.evidence],
                ),
            )
            self._task(
                run,
                7,
                self.AGENTS[6],
                [{"impactId": impact.id} for impact in impacts],
                lambda: (
                    {
                        "actions": [
                            action for impact in impacts for action in impact.recommended_actions
                        ]
                    },
                    min((impact.confidence for impact in impacts), default=0.0),
                    [{"impactId": impact.id, "evidence": impact.evidence} for impact in impacts],
                ),
            )

            decision = self.verification_agent.verify(previous, changes, impacts)
            verification = RegulatoryVerificationResult(
                agent_run_id=run.id,
                status=decision.status,
                confidence=decision.confidence,
                issues=decision.issues,
                checked_claims=decision.checked_claims,
                rejected_claims=decision.rejected_claims,
            )
            self.session.add(verification)
            self.session.flush()
            self._task(
                run,
                8,
                self.AGENTS[7],
                [{"changeId": change.id} for change in changes]
                + [{"impactId": impact.id} for impact in impacts],
                lambda: (
                    {
                        "status": verification.status.value,
                        "issues": verification.issues,
                        "checkedClaims": verification.checked_claims,
                        "rejectedClaims": verification.rejected_claims,
                    },
                    verification.confidence,
                    [],
                ),
            )
            run.status = verification.status
            run.completed_at = datetime.now(UTC)
            if run.status == AgentRunStatus.COMPLETED:
                version.status = RegulatoryDocumentStatus.ANALYZED
            else:
                version.status = RegulatoryDocumentStatus.NEEDS_HUMAN_REVIEW
            self.session.commit()
            return run
        except Exception as exc:
            self.session.rollback()
            failed_run = self.repository.run(run.id)
            if failed_run:
                failed_run.status = AgentRunStatus.FAILED
                failed_run.error_message = type(exc).__name__
                failed_run.completed_at = datetime.now(UTC)
                self.session.commit()
            raise

    def _task(
        self,
        run: RegulatoryAgentRun,
        sequence: int,
        agent_name: str,
        input_references: list[dict[str, Any]],
        execute: Callable[[], tuple[dict[str, Any], float, list[dict[str, Any]]]],
    ) -> None:
        now = datetime.now(UTC)
        task = RegulatoryAgentTask(
            agent_run_id=run.id,
            agent_name=agent_name,
            sequence_number=sequence,
            status=AgentRunStatus.RUNNING,
            input_references=input_references,
            started_at=now,
        )
        self.session.add(task)
        self.session.flush()
        result, confidence, evidence = execute()
        task.status = AgentRunStatus.COMPLETED
        task.completed_at = datetime.now(UTC)
        self.session.add(
            RegulatoryAgentOutput(
                agent_task_id=task.id,
                agent_name=agent_name,
                result=result,
                confidence=max(0.0, min(1.0, confidence)),
                evidence=evidence,
            )
        )
        self.session.commit()

    @staticmethod
    def _section_evidence(section) -> dict[str, Any]:
        return {
            "sectionId": section.id,
            "location": section.legal_location,
            "quote": section.content[:300],
        }

    @staticmethod
    def _change_result(change: RegulatoryChange) -> dict[str, Any]:
        return {
            "changeId": change.id,
            "changeType": change.change_type.value,
            "oldValue": change.old_value,
            "newValue": change.new_value,
            "effectiveYear": change.effective_year,
            "oldLocation": change.old_location,
            "newLocation": change.new_location,
            "summary": change.summary,
        }


def version_document_workspace(version: RegulatoryDocumentVersion, session: Session) -> str:
    from app.model.documents import Document

    document = session.get(Document, version.document_id)
    return document.workspace_id if document else ""

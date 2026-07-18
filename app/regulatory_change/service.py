from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, PayloadTooLargeError
from app.model.documents import Document
from app.regulatory_change.agents import LegalResearchAgent
from app.regulatory_change.diff import SemanticDiffAgent
from app.regulatory_change.intake import RegulatoryDocumentIntakeAgent
from app.regulatory_change.models import (
    RegulatoryDocumentFamily,
    RegulatoryDocumentVersion,
    RegulatoryImpact,
    RegulatoryProject,
    RegulatorySection,
)
from app.regulatory_change.orchestrator import RegulatoryOrchestrator
from app.regulatory_change.repository import RegulatoryRepository
from app.regulatory_change.schemas import (
    AgentRunData,
    AgentTaskData,
    AnalyzeData,
    ChangeData,
    ImpactData,
    ProjectCreate,
    ProjectData,
    RegulatoryDocumentData,
    RegulatorySectionData,
    RegulatoryUploadData,
    RegulatoryUploadMetadata,
    TimelineEntry,
    VerificationData,
)
from app.service.documents import DocumentService


class RegulatoryChangeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = RegulatoryRepository(session)
        self.intake = RegulatoryDocumentIntakeAgent()
        self.diff = SemanticDiffAgent()

    def upload(
        self,
        upload: UploadFile,
        metadata: RegulatoryUploadMetadata,
        document_service: DocumentService,
    ) -> RegulatoryUploadData:
        upload.file.seek(0)
        max_bytes = document_service.settings.max_upload_size_bytes
        content = upload.file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise PayloadTooLargeError(max_bytes)
        upload.file.seek(0)
        raw_text = self.intake.extract_text(
            content,
            filename=upload.filename or "document",
            mime_type=(upload.content_type or "application/octet-stream").lower(),
        )
        parsed_sections = self.intake.parse_sections(raw_text)
        family_key = self.intake.family_key(
            metadata.title,
            metadata.document_number,
            metadata.family_key,
        )
        family = self.repository.family(metadata.workspace_id, family_key)
        if family and family.document_type != metadata.document_type:
            raise ConflictError(
                "DOCUMENT_FAMILY_TYPE_MISMATCH",
                "Loại văn bản không khớp với document family đã tồn tại.",
                {"familyId": family.id, "expectedType": family.document_type},
            )
        if family and any(
            version.effective_date == metadata.effective_date
            for version in self.repository.versions(family.id)
        ):
            raise ConflictError(
                "DOCUMENT_VERSION_EFFECTIVE_DATE_EXISTS",
                "Document family đã có phiên bản với cùng ngày hiệu lực.",
                {"familyId": family.id, "effectiveDate": metadata.effective_date.isoformat()},
            )
        upload_result = document_service.upload(
            metadata.workspace_id,
            upload,
            display_name=metadata.title,
        )
        if family is None:
            family = RegulatoryDocumentFamily(
                workspace_id=metadata.workspace_id,
                family_key=family_key,
                canonical_title=metadata.title,
                document_type=metadata.document_type,
            )
            self.session.add(family)
            self.session.flush()
        version_number = len(self.repository.versions(family.id)) + 1
        version = RegulatoryDocumentVersion(
            family_id=family.id,
            document_id=upload_result.document_id,
            version_number=version_number,
            title=metadata.title,
            document_number=metadata.document_number,
            legal_document_type=metadata.document_type,
            issuing_agency=metadata.issuing_agency,
            issued_date=metadata.issued_date,
            effective_date=metadata.effective_date,
            domain=metadata.domain,
            applicable_subjects=metadata.applicable_subjects,
            raw_text=raw_text,
            executive_summary=self.intake.executive_summary(raw_text),
        )
        self.session.add(version)
        self.session.flush()
        self.session.add_all(
            [
                RegulatorySection(
                    document_version_id=version.id,
                    section_type=section.section_type,
                    label=section.label,
                    title=section.title,
                    legal_location=section.legal_location,
                    content=section.content,
                    normalized_content=self.intake._normalize(section.content),
                    order_index=section.order_index,
                    page_start=section.page_start,
                    page_end=section.page_end,
                )
                for section in parsed_sections
            ]
        )
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            document_service.soft_delete(upload_result.document_id)
            raise ConflictError(
                "REGULATORY_VERSION_CONFLICT",
                "Không thể tạo phiên bản do dữ liệu family/version bị trùng.",
            ) from exc
        self.session.refresh(version)
        return RegulatoryUploadData(
            **self._document_data(version, family).model_dump(),
            processing_status=upload_result.status.value,
        )

    def list_documents(self, workspace_id: str | None = None) -> list[RegulatoryDocumentData]:
        query = (
            select(RegulatoryDocumentVersion, RegulatoryDocumentFamily)
            .join(
                RegulatoryDocumentFamily,
                RegulatoryDocumentFamily.id == RegulatoryDocumentVersion.family_id,
            )
            .order_by(RegulatoryDocumentVersion.created_at.desc())
        )
        if workspace_id:
            query = query.where(RegulatoryDocumentFamily.workspace_id == workspace_id)
        return [
            self._document_data(version, family) for version, family in self.session.execute(query)
        ]

    def profile(self, document_id: str) -> RegulatoryDocumentData:
        version = self._version(document_id)
        family = self.session.get(RegulatoryDocumentFamily, version.family_id)
        assert family is not None
        return self._document_data(version, family)

    def summary(self, document_id: str) -> dict[str, Any]:
        version = self._version(document_id)
        sections = self.repository.sections(version.id)
        values = self.diff.extract_current_values(version, sections)
        return {
            "documentId": document_id,
            "executiveSummary": version.executive_summary,
            "importantValues": values,
            "effectiveDate": version.effective_date.isoformat(),
            "applicableSubjects": version.applicable_subjects,
            "evidence": [
                {
                    "sectionId": section.id,
                    "location": section.legal_location,
                    "quote": section.content[:300],
                }
                for section in sections[:5]
            ],
        }

    def sections(self, document_id: str) -> list[RegulatorySectionData]:
        version = self._version(document_id)
        return [
            RegulatorySectionData.model_validate(
                {
                    "id": section.id,
                    "section_type": section.section_type,
                    "label": section.label,
                    "title": section.title,
                    "legal_location": section.legal_location,
                    "content": section.content,
                    "order_index": section.order_index,
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                }
            )
            for section in self.repository.sections(version.id)
        ]

    def versions(self, document_id: str) -> list[RegulatoryDocumentData]:
        current = self._version(document_id)
        family = self.session.get(RegulatoryDocumentFamily, current.family_id)
        assert family is not None
        return [
            self._document_data(version, family) for version in self.repository.versions(family.id)
        ]

    def changes(self, document_id: str) -> list[ChangeData]:
        version = self._version(document_id)
        return [self._change_data(change) for change in self.repository.changes(version.id)]

    def timeline(self, document_id: str) -> list[TimelineEntry]:
        current = self._version(document_id)
        entries = []
        for version in reversed(self.repository.versions(current.family_id)):
            entries.append(
                TimelineEntry(
                    document_id=version.document_id,
                    version_number=version.version_number,
                    issued_date=version.issued_date,
                    effective_date=version.effective_date,
                    values=self.diff.extract_current_values(
                        version, self.repository.sections(version.id)
                    ),
                )
            )
        return entries

    def legal_relations(self, document_id: str) -> list[dict[str, Any]]:
        version = self._version(document_id)
        research, confidence, evidence = LegalResearchAgent().research(version)
        return [
            {
                "relationshipType": "CITES",
                "citedReference": reference,
                "status": "EXTRACTED_NOT_EXTERNALLY_VERIFIED",
                "confidence": confidence,
                "evidence": evidence[index],
            }
            for index, reference in enumerate(research["references"])
        ]

    def analyze(self, document_id: str, *, force: bool = False) -> AnalyzeData:
        version = self._version(document_id)
        run = RegulatoryOrchestrator(self.session).analyze(version, force=force)
        return AnalyzeData(
            run=self.run_data(run.id),
            changes=self.changes(document_id),
            impacts=self.impacts(document_version_id=version.id),
        )

    def create_project(self, payload: ProjectCreate) -> ProjectData:
        if self.repository.project_by_code(payload.workspace_id, payload.project_code):
            raise ConflictError(
                "PROJECT_CODE_EXISTS",
                "Mã đề án đã tồn tại.",
                {"projectCode": payload.project_code},
            )
        project = RegulatoryProject(**payload.model_dump())
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return ProjectData.model_validate(project)

    def list_projects(self, workspace_id: str | None = None) -> list[ProjectData]:
        return [
            ProjectData.model_validate(project)
            for project in self.repository.projects(workspace_id)
        ]

    def get_project(self, project_id: str) -> ProjectData:
        return ProjectData.model_validate(self._project(project_id))

    def impacts(
        self,
        *,
        document_version_id: str | None = None,
        project_id: str | None = None,
        department: str | None = None,
    ) -> list[ImpactData]:
        return [
            self._impact_data(impact)
            for impact in self.repository.impacts(
                document_version_id=document_version_id,
                project_id=project_id,
                department=department,
            )
        ]

    def impact(self, impact_id: str) -> ImpactData:
        impact = self.repository.impact(impact_id)
        if impact is None:
            raise NotFoundError("REGULATORY_IMPACT", impact_id)
        return self._impact_data(impact)

    def review_impact(
        self, impact_id: str, *, status: str, reviewed_by: str, note: str | None
    ) -> ImpactData:
        impact = self.repository.impact(impact_id)
        if impact is None:
            raise NotFoundError("REGULATORY_IMPACT", impact_id)
        impact.review_status = status
        impact.reviewed_by = reviewed_by
        impact.review_note = note
        impact.reviewed_at = datetime.now(UTC)
        self.session.commit()
        return self._impact_data(impact)

    def run_data(self, run_id: str) -> AgentRunData:
        run = self.repository.run(run_id)
        if run is None:
            raise NotFoundError("REGULATORY_AGENT_RUN", run_id)
        version = self.repository.version(run.document_version_id)
        assert version is not None
        tasks = []
        for task in self.repository.tasks(run.id):
            output = self.repository.output(task.id)
            tasks.append(
                AgentTaskData(
                    id=task.id,
                    agent_name=task.agent_name,
                    sequence_number=task.sequence_number,
                    status=task.status,
                    input_references=task.input_references,
                    result=output.result if output else None,
                    confidence=output.confidence if output else None,
                    evidence=output.evidence if output else [],
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                    error_message=task.error_message,
                )
            )
        verification = self.repository.verification(run.id)
        return AgentRunData(
            id=run.id,
            document_version_id=run.document_version_id,
            document_id=version.document_id,
            status=run.status,
            attempt=run.attempt,
            tasks=tasks,
            verification=(
                VerificationData(
                    status=verification.status,
                    confidence=verification.confidence,
                    issues=verification.issues,
                    checked_claims=verification.checked_claims,
                    rejected_claims=verification.rejected_claims,
                )
                if verification
                else None
            ),
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            created_at=run.created_at,
        )

    def retry_run(self, run_id: str) -> AnalyzeData:
        run = self.repository.run(run_id)
        if run is None:
            raise NotFoundError("REGULATORY_AGENT_RUN", run_id)
        version = self.repository.version(run.document_version_id)
        assert version is not None
        return self.analyze(version.document_id, force=True)

    def _version(self, document_id: str) -> RegulatoryDocumentVersion:
        if self.session.get(Document, document_id) is None:
            raise NotFoundError("DOCUMENT", document_id)
        version = self.repository.version_by_document(document_id)
        if version is None:
            raise NotFoundError("REGULATORY_DOCUMENT_PROFILE", document_id)
        return version

    def _project(self, project_id: str) -> RegulatoryProject:
        project = self.repository.project(project_id)
        if project is None:
            raise NotFoundError("REGULATORY_PROJECT", project_id)
        return project

    def _document_data(
        self,
        version: RegulatoryDocumentVersion,
        family: RegulatoryDocumentFamily,
    ) -> RegulatoryDocumentData:
        return RegulatoryDocumentData(
            id=version.id,
            document_id=version.document_id,
            family_id=version.family_id,
            family_key=family.family_key,
            version_number=version.version_number,
            title=version.title,
            document_number=version.document_number,
            document_type=version.legal_document_type,
            issuing_agency=version.issuing_agency,
            issued_date=version.issued_date,
            effective_date=version.effective_date,
            domain=version.domain,
            applicable_subjects=version.applicable_subjects,
            status=version.status.value,
            executive_summary=version.executive_summary,
            created_at=version.created_at,
        )

    @staticmethod
    def _change_data(change) -> ChangeData:
        return ChangeData(
            id=change.id,
            change_type=change.change_type,
            status=change.status,
            fact_key=change.fact_key,
            old_value=change.old_value,
            new_value=change.new_value,
            effective_year=change.effective_year,
            old_location=change.old_location,
            new_location=change.new_location,
            summary=change.summary,
            confidence=change.confidence,
            evidence=change.evidence,
        )

    def _impact_data(self, impact: RegulatoryImpact) -> ImpactData:
        version = self.repository.version(impact.document_version_id)
        project = self._project(impact.project_id)
        assert version is not None
        return ImpactData(
            id=impact.id,
            document_version_id=impact.document_version_id,
            document_id=version.document_id,
            project_id=impact.project_id,
            project_name=project.name,
            agent_run_id=impact.agent_run_id,
            impact_level=impact.impact_level,
            confidence=impact.confidence,
            reason=impact.reason,
            affected_areas=impact.affected_areas,
            departments=impact.departments,
            recommended_actions=impact.recommended_actions,
            evidence=impact.evidence,
            review_status=impact.review_status,
            reviewed_by=impact.reviewed_by,
            review_note=impact.review_note,
            reviewed_at=impact.reviewed_at,
            created_at=impact.created_at,
        )

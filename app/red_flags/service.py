from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.citations.repository import CitationRepository
from app.citations.schemas import CitationDraft, CitationOwnerType
from app.citations.validator import CitationValidator
from app.documents.interfaces import DocumentChunkContract, DocumentChunkReader
from app.knowledge_graph.reader import KnowledgeGraphReader, SqlAlchemyKnowledgeGraphReader
from app.knowledge_graph.schemas import KnowledgeGraphView
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.schemas import TaskType
from app.orchestrator.executor import WorkflowExecutor
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.schemas import ExecutionStep, StepStatus
from app.red_flags.models import CriticalQuestion
from app.red_flags.prompts import (
    CRITICAL_QUESTION_PROMPT_VERSION,
    QUESTION_VERIFICATION_PROMPT_VERSION,
    RED_FLAG_VERIFICATION_PROMPT_VERSION,
)
from app.red_flags.reader import RedFlagReader, SqlAlchemyRedFlagReader
from app.red_flags.repository import CriticalQuestionRepository, RedFlagRepository
from app.red_flags.rules import RedFlagRuleEngine
from app.red_flags.schemas import (
    CriticalQuestionDraft,
    CriticalQuestionGenerationResult,
    CriticalQuestionOutput,
    CriticalQuestionView,
    QuestionVerificationOutput,
    QuestionVerificationStatus,
    RedFlagDraft,
    RedFlagOutput,
    RedFlagSeverity,
    VerifiedCriticalQuestion,
    VerifiedCriticalQuestionOutput,
)
from app.red_flags.verification import HighSeverityFlagVerifier


class RedFlagService:
    def __init__(
        self,
        session: Session,
        *,
        gateway: ModelGateway,
        planner: ExecutionPlanner,
        citation_validator: CitationValidator,
        graph_reader: KnowledgeGraphReader | None = None,
        rule_engine: RedFlagRuleEngine | None = None,
    ) -> None:
        self.session = session
        self.gateway = gateway
        self.planner = planner
        self.citation_validator = citation_validator
        self.graph_reader = graph_reader or SqlAlchemyKnowledgeGraphReader(session)
        self.rule_engine = rule_engine or RedFlagRuleEngine()
        self.repository = RedFlagRepository(session)
        self.citation_repository = CitationRepository(session)

    def evaluate(
        self,
        document_id: str,
        *,
        private: bool = False,
        graph: KnowledgeGraphView | None = None,
    ) -> tuple[str, list]:
        graph = graph or self.graph_reader.get_graph(document_id)
        if graph is None:
            raise ValueError("Knowledge graph must be generated before red-flag evaluation")
        plan = self.planner.red_flag_plan(document_id, private=private)

        def detect(
            step: ExecutionStep,
            executor: str,
            dependencies: dict[str, Any],
        ) -> RedFlagOutput:
            del step, executor, dependencies
            return RedFlagOutput(flags=self.rule_engine.evaluate(graph))

        def verify(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> RedFlagOutput:
            detected = RedFlagOutput.model_validate(dependencies["detect-red-flags"])
            return HighSeverityFlagVerifier(
                self.gateway,
                self.citation_validator,
            ).verify(
                detected.flags,
                document_id=document_id,
                model_alias=model_alias,
                timeout_seconds=step.timeout_seconds,
                workflow_id=plan.workflow_id,
                step_id=step.step_id,
                context=graph.model_dump(mode="json", by_alias=True),
            )

        result = WorkflowExecutor(self.session).execute(
            plan,
            {
                TaskType.RED_FLAG_DETECTION: detect,
                TaskType.RED_FLAG_VERIFICATION: verify,
            },
        )
        final_step = result.steps[-1]
        if final_step.status != StepStatus.COMPLETED or final_step.output is None:
            return plan.workflow_id, []
        output = RedFlagOutput.model_validate(final_step.output)
        for draft in output.flags:
            stored = self.repository.add(
                document_id=document_id,
                graph_version_id=graph.version_id,
                workflow_id=plan.workflow_id,
                draft=draft,
            )
            for citation in draft.citations:
                validated = self.citation_validator.validate(
                    citation,
                    expected_document_id=document_id,
                )
                if validated.valid:
                    self.citation_repository.add_validated(
                        validated,
                        owner_type=CitationOwnerType.RED_FLAG,
                        owner_id=stored.id,
                    )
        self.session.commit()
        views = SqlAlchemyRedFlagReader(self.session).list_for_document(document_id)
        return plan.workflow_id, views

    def _citations_valid(self, citations: list[CitationDraft], document_id: str) -> bool:
        return all(
            result.valid
            for result in self.citation_validator.validate_all(
                citations,
                expected_document_id=document_id,
            )
        )

    @staticmethod
    def _verification_prompt(flags: list[RedFlagDraft], graph: KnowledgeGraphView) -> str:
        flags_json = json.dumps(
            [flag.model_dump(mode="json", by_alias=True) for flag in flags],
            ensure_ascii=False,
        )
        return (
            f"Prompt version: {RED_FLAG_VERIFICATION_PROMPT_VERSION}. Kiểm chứng từng cảnh "
            "báo HIGH/CRITICAL bằng citation. verified=true chỉ khi nguồn đủ chứng minh đúng "
            "vấn đề; không bổ sung fact.\n"
            f"flags={flags_json}\n"
            f"graph={graph.model_dump_json(by_alias=True)}"
        )


class CriticalQuestionService:
    _generic_subjects = {"vấn đề", "nội dung", "quy định", "tài liệu", "văn bản"}

    def __init__(
        self,
        session: Session,
        *,
        gateway: ModelGateway,
        planner: ExecutionPlanner,
        chunk_reader: DocumentChunkReader,
        citation_validator: CitationValidator,
        red_flag_reader: RedFlagReader | None = None,
    ) -> None:
        self.session = session
        self.gateway = gateway
        self.planner = planner
        self.chunk_reader = chunk_reader
        self.citation_validator = citation_validator
        self.red_flag_reader = red_flag_reader or SqlAlchemyRedFlagReader(session)
        self.repository = CriticalQuestionRepository(session)
        self.flag_repository = RedFlagRepository(session)
        self.citation_repository = CitationRepository(session)

    def generate(
        self,
        document_id: str,
        *,
        private: bool = False,
    ) -> CriticalQuestionGenerationResult:
        flags = self.red_flag_reader.list_for_document(document_id)
        chunks = self._related_chunks(flags)
        plan = self.planner.critical_questions_plan(document_id, private=private)

        def generate_questions(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> CriticalQuestionOutput:
            del dependencies
            if not flags:
                return CriticalQuestionOutput(questions=[])
            output = self.gateway.generate_structured(
                model_alias=model_alias,
                prompt=self._generation_prompt(flags, chunks),
                output_schema=CriticalQuestionOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            valid = [
                question
                for question in output.questions[:5]
                if self._question_valid(question, flags, document_id)
            ]
            return CriticalQuestionOutput(questions=valid)

        def verify_questions(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> VerifiedCriticalQuestionOutput:
            generated = CriticalQuestionOutput.model_validate(
                dependencies["generate-critical-questions"]
            )
            complex_indices = [
                index
                for index, question in enumerate(generated.questions)
                if question.severity in {RedFlagSeverity.HIGH, RedFlagSeverity.CRITICAL}
            ]
            by_index = {}
            if complex_indices:
                verification = self.gateway.generate_structured(
                    model_alias=model_alias,
                    prompt=self._question_verification_prompt(generated, chunks),
                    output_schema=QuestionVerificationOutput,
                    timeout_seconds=step.timeout_seconds,
                    metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
                )
                by_index = {
                    decision.question_index: decision for decision in verification.decisions
                }
            verified: list[VerifiedCriticalQuestion] = []
            for index, question in enumerate(generated.questions):
                if index not in complex_indices:
                    verified.append(
                        VerifiedCriticalQuestion(
                            draft=question,
                            verificationStatus=QuestionVerificationStatus.VERIFIED,
                            verificationModel=None,
                        )
                    )
                    continue
                decision = by_index.get(index)
                if decision and decision.verified and decision.evidence_sufficient:
                    verified.append(
                        VerifiedCriticalQuestion(
                            draft=question,
                            verificationStatus=QuestionVerificationStatus.VERIFIED,
                            verificationModel=model_alias,
                        )
                    )
            return VerifiedCriticalQuestionOutput(questions=verified[:5])

        result = WorkflowExecutor(self.session).execute(
            plan,
            {
                TaskType.CRITICAL_QUESTION_GENERATION: generate_questions,
                TaskType.CRITICAL_QUESTION_VERIFICATION: verify_questions,
            },
        )
        final_step = result.steps[-1]
        if final_step.status != StepStatus.COMPLETED or final_step.output is None:
            return CriticalQuestionGenerationResult(workflowId=plan.workflow_id, questions=[])
        batch = VerifiedCriticalQuestionOutput.model_validate(final_step.output)
        stored_views = []
        flag_ids_by_issue: dict[str, str] = {}
        for flag in flags:
            flag_ids_by_issue.setdefault(flag.issue_type.value, flag.id)
        for item in batch.questions[:5]:
            stored = self.repository.add(
                document_id=document_id,
                workflow_id=plan.workflow_id,
                draft=item.draft,
                verification_status=item.verification_status,
                verification_model=item.verification_model,
                red_flag_id=flag_ids_by_issue.get(item.draft.issue_type.value),
            )
            for citation in item.draft.citations:
                validated = self.citation_validator.validate_or_raise(
                    citation,
                    expected_document_id=document_id,
                )
                self.citation_repository.add_validated(
                    validated,
                    owner_type=CitationOwnerType.CRITICAL_QUESTION,
                    owner_id=stored.id,
                )
            stored_views.append(self._question_view(stored))
        self.session.commit()
        return CriticalQuestionGenerationResult(
            workflowId=plan.workflow_id,
            questions=stored_views,
        )

    def list_for_document(self, document_id: str) -> list[CriticalQuestionView]:
        return [
            self._question_view(question)
            for question in self.repository.list_for_document(document_id)
        ]

    def _related_chunks(self, flags: list) -> list[DocumentChunkContract]:
        chunks: dict[str, DocumentChunkContract] = {}
        for flag in flags:
            for citation in flag.citations:
                if citation.chunk_id not in chunks:
                    chunks[citation.chunk_id] = self.chunk_reader.get_chunk(citation.chunk_id)
        return list(chunks.values())

    def _question_valid(
        self,
        question: CriticalQuestionDraft,
        flags: list,
        document_id: str,
    ) -> bool:
        matching = [flag for flag in flags if flag.issue_type == question.issue_type]
        if not matching:
            return False
        severity_rank = {
            RedFlagSeverity.LOW: 0,
            RedFlagSeverity.MEDIUM: 1,
            RedFlagSeverity.HIGH: 2,
            RedFlagSeverity.CRITICAL: 3,
        }
        expected_severity = max(
            (flag.severity for flag in matching),
            key=severity_rank.__getitem__,
        )
        if question.severity != expected_severity:
            return False
        evidence_chunk_ids = {citation.chunk_id for flag in matching for citation in flag.citations}
        if not evidence_chunk_ids or any(
            citation.chunk_id not in evidence_chunk_ids for citation in question.citations
        ):
            return False
        if question.related_subject.casefold().strip() in self._generic_subjects:
            return False
        if not all(
            result.valid
            for result in self.citation_validator.validate_all(
                question.citations,
                expected_document_id=document_id,
            )
        ):
            return False
        subject_tokens = [
            token.casefold().strip(".,;:()")
            for token in question.related_subject.split()
            if len(token.strip(".,;:()")) >= 4
        ]
        searchable = f"{question.question} {question.reason}".casefold()
        return bool(subject_tokens) and any(token in searchable for token in subject_tokens)

    def _question_view(self, question: CriticalQuestion) -> CriticalQuestionView:
        citations = [
            self.citation_repository.view(citation)
            for citation in self.citation_repository.list_for_owner(
                CitationOwnerType.CRITICAL_QUESTION,
                question.id,
            )
        ]
        return CriticalQuestionView(
            id=question.id,
            documentId=question.document_id,
            workflowId=question.workflow_id,
            question=question.question,
            reason=question.reason,
            issueType=question.issue_type,
            severity=question.severity,
            relatedSubject=question.related_subject,
            sourceLocation=question.source_location,
            riskIfUnresolved=question.risk_if_unresolved,
            citations=citations,
            verificationStatus=question.verification_status,
            verificationModel=question.verification_model,
            createdAt=question.created_at,
        )

    @staticmethod
    def _chunks_payload(chunks: list[DocumentChunkContract]) -> list[dict[str, Any]]:
        return [
            {
                "chunkId": chunk.id,
                "documentId": chunk.document_id,
                "content": chunk.content,
                "article": chunk.article,
                "clause": chunk.clause,
                "point": chunk.point,
                "pageStart": chunk.pdf_page_start,
                "pageEnd": chunk.pdf_page_end,
                "boundingBoxes": chunk.bounding_boxes,
            }
            for chunk in chunks
        ]

    def _generation_prompt(self, flags: list, chunks: list[DocumentChunkContract]) -> str:
        schema_json = json.dumps(
            CriticalQuestionOutput.model_json_schema(by_alias=True),
            ensure_ascii=False,
        )
        flags_json = json.dumps(
            [flag.model_dump(mode="json", by_alias=True) for flag in flags],
            ensure_ascii=False,
        )
        return (
            f"Prompt version: {CRITICAL_QUESTION_PROMPT_VERSION}. Sinh tối đa 5 câu hỏi phản "
            "biện, không tạo câu hỏi chung chung. Mỗi câu phải nêu vấn đề, chủ thể/nhiệm vụ, "
            "vị trí nguồn, lý do cần hỏi và rủi ro nếu không làm rõ. Citation phải trích đúng "
            "chunk. Chỉ hỏi về red flags được cung cấp.\n"
            f"schema={schema_json}\n"
            f"flags={flags_json}\n"
            f"chunks={json.dumps(self._chunks_payload(chunks), ensure_ascii=False)}"
        )

    def _question_verification_prompt(
        self,
        output: CriticalQuestionOutput,
        chunks: list[DocumentChunkContract],
    ) -> str:
        return (
            f"Prompt version: {QUESTION_VERIFICATION_PROMPT_VERSION}. Chỉ kiểm chứng câu hỏi "
            "HIGH/CRITICAL. Xác nhận question cụ thể và bằng chứng đủ chứng minh vấn đề; không "
            "viết lại câu hỏi.\n"
            f"questions={output.model_dump_json(by_alias=True)}\n"
            f"chunks={json.dumps(self._chunks_payload(chunks), ensure_ascii=False)}"
        )

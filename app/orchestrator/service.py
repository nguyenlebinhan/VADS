from __future__ import annotations

import json
from typing import Any

from pydantic import Field
from sqlalchemy.orm import Session

from app.citations.repository import CitationRepository
from app.citations.schemas import CitationOwnerType
from app.citations.validator import CitationValidator
from app.common.contracts import APIModel
from app.documents.interfaces import DocumentChunkContract, DocumentChunkReader
from app.knowledge_graph.reader import SqlAlchemyKnowledgeGraphReader
from app.knowledge_graph.repository import KnowledgeGraphRepository
from app.knowledge_graph.schemas import (
    GraphExtractionOutput,
    GraphVersionStatus,
    KnowledgeGraphView,
    RelationVerificationOutput,
    VerificationStatus,
)
from app.knowledge_graph.service import KnowledgeGraphService
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.schemas import TaskType
from app.orchestrator.chunk_snapshot import SnapshotDocumentChunkReader
from app.orchestrator.executor import WorkflowExecutor
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.repository import WorkflowRepository
from app.orchestrator.schemas import (
    ExecutionPlan,
    ExecutionStep,
    StepStatus,
    WorkflowExecutionResult,
    WorkflowStatus,
)
from app.red_flags.prompts import RED_FLAG_VERIFICATION_PROMPT_VERSION
from app.red_flags.reader import SqlAlchemyRedFlagReader
from app.red_flags.repository import CriticalQuestionRepository, RedFlagRepository
from app.red_flags.rules import RedFlagRuleEngine
from app.red_flags.schemas import (
    CriticalQuestionOutput,
    QuestionVerificationOutput,
    QuestionVerificationStatus,
    RedFlagDraft,
    RedFlagOutput,
    RedFlagSeverity,
    RedFlagStatus,
    RedFlagVerificationOutput,
    VerifiedCriticalQuestion,
    VerifiedCriticalQuestionOutput,
)
from app.red_flags.service import CriticalQuestionService
from app.summaries.prompts import SUMMARY_PROMPT_VERSION
from app.summaries.repository import SummaryRepository
from app.summaries.schemas import DocumentSummaryOutput, SummaryStatus
from app.summaries.service import SummaryService

ANALYSIS_BATCH_MAX_CHUNKS = 12
ANALYSIS_BATCH_MAX_TOKENS = 12_000


class DocumentAnalysisResult(APIModel):
    workflow_id: str
    status: WorkflowStatus
    summary_id: str | None = None
    graph_version_id: str | None = None
    red_flag_count: int = 0
    critical_question_count: int = 0
    steps: list[dict[str, Any]] = Field(default_factory=list)


class DocumentAnalysisOrchestrator:
    """Runs one multi-model DAG and persists all validated domain artifacts."""

    def __init__(
        self,
        session: Session,
        *,
        gateway: ModelGateway,
        planner: ExecutionPlanner,
        chunk_reader: DocumentChunkReader,
        citation_validator: CitationValidator,
    ) -> None:
        self.session = session
        self.gateway = gateway
        self.planner = planner
        self.chunk_reader = chunk_reader
        self.citation_validator = citation_validator

    def analyze(
        self,
        document_id: str,
        *,
        private: bool = False,
        plan: ExecutionPlan | None = None,
    ) -> DocumentAnalysisResult:
        chunks = self.chunk_reader.list_chunks(document_id)
        chunk_batches = self._chunk_batches(chunks)
        snapshot = SnapshotDocumentChunkReader(chunks)
        validator = CitationValidator(
            snapshot,
            document_exists=lambda candidate: candidate == document_id,
        )
        persist_plan = plan is None
        plan = plan or self.planner.analysis_plan(document_id, private=private)
        summary_helper = SummaryService(
            self.session,
            gateway=self.gateway,
            planner=self.planner,
            chunk_reader=snapshot,
            citation_validator=validator,
        )
        graph_helper = KnowledgeGraphService(
            self.session,
            gateway=self.gateway,
            planner=self.planner,
            chunk_reader=snapshot,
            citation_validator=validator,
        )
        question_helper = CriticalQuestionService(
            self.session,
            gateway=self.gateway,
            planner=self.planner,
            chunk_reader=snapshot,
            citation_validator=validator,
        )
        rule_engine = RedFlagRuleEngine()

        def summary_handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            del dependencies
            items = []
            rejected = []
            for batch_index, batch in enumerate(chunk_batches):
                output = self.gateway.generate_structured(
                    model_alias=model,
                    prompt=summary_helper._summary_prompt(
                        document_id,
                        batch,
                        SUMMARY_PROMPT_VERSION,
                    ),
                    output_schema=DocumentSummaryOutput,
                    timeout_seconds=step.timeout_seconds,
                    metadata={
                        "workflowId": plan.workflow_id,
                        "stepId": step.step_id,
                        "batchIndex": batch_index,
                        "batchCount": len(chunk_batches),
                    },
                )
                validated = summary_helper._validate_and_repair(
                    output,
                    document_id=document_id,
                    chunks=batch,
                    model_alias=model,
                    timeout_seconds=step.timeout_seconds,
                    workflow_id=plan.workflow_id,
                )
                items.extend(validated.items)
                rejected.extend(validated.rejected_items)
            return DocumentSummaryOutput(items=items, rejectedItems=rejected)

        def extract_handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            del dependencies
            nodes = []
            edges = []
            for batch_index, batch in enumerate(chunk_batches):
                extracted = self.gateway.generate_structured(
                    model_alias=model,
                    prompt=graph_helper._extraction_prompt(document_id, batch),
                    output_schema=GraphExtractionOutput,
                    timeout_seconds=step.timeout_seconds,
                    metadata={
                        "workflowId": plan.workflow_id,
                        "stepId": step.step_id,
                        "batchIndex": batch_index,
                        "batchCount": len(chunk_batches),
                    },
                )
                prefix = f"b{batch_index}-"
                node_ids = {node.node_id: f"{prefix}{node.node_id}" for node in extracted.nodes}
                nodes.extend(
                    node.model_copy(update={"node_id": node_ids[node.node_id]})
                    for node in extracted.nodes
                )
                edges.extend(
                    edge.model_copy(
                        update={
                            "edge_id": f"{prefix}{edge.edge_id}",
                            "source_node_id": node_ids[edge.source_node_id],
                            "target_node_id": node_ids[edge.target_node_id],
                        }
                    )
                    for edge in extracted.edges
                    if edge.source_node_id in node_ids and edge.target_node_id in node_ids
                )
            return GraphExtractionOutput(nodes=nodes, edges=edges)

        def normalize_handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            extracted = GraphExtractionOutput.model_validate(
                dependencies["extract-entities-relations"]
            )
            normalized = self.gateway.generate_structured(
                model_alias=model,
                prompt=graph_helper._normalization_prompt(extracted),
                output_schema=GraphExtractionOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            return graph_helper.deduplicator.deduplicate(
                graph_helper.normalizer.normalize(normalized)
            )

        def relation_handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            graph = GraphExtractionOutput.model_validate(dependencies["normalize-graph"])
            complex_edges = graph_helper._complex_edges(graph)
            if not complex_edges:
                return graph
            decisions = self.gateway.generate_structured(
                model_alias=model,
                prompt=graph_helper._verification_prompt(
                    graph,
                    complex_edges,
                    self._evidence_chunks(chunks, complex_edges),
                ),
                output_schema=RelationVerificationOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            by_id = {decision.edge_id: decision for decision in decisions.verifications}
            complex_ids = {edge.edge_id for edge in complex_edges}
            edges = []
            for edge in graph.edges:
                decision = by_id.get(edge.edge_id)
                if edge.edge_id not in complex_ids:
                    edges.append(edge)
                elif decision and decision.verified and decision.evidence_sufficient:
                    edges.append(
                        edge.model_copy(update={"verification_status": VerificationStatus.VERIFIED})
                    )
                else:
                    edges.append(
                        edge.model_copy(
                            update={"verification_status": VerificationStatus.NEEDS_REVIEW}
                        )
                    )
            return GraphExtractionOutput(nodes=graph.nodes, edges=edges)

        def flag_handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            del step, model
            graph = GraphExtractionOutput.model_validate(dependencies["verify-complex-relations"])
            return RedFlagOutput(flags=rule_engine.evaluate(graph))

        def flag_verifier(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            detected = RedFlagOutput.model_validate(dependencies["detect-red-flags"])
            eligible: list[RedFlagDraft] = []
            output: list[RedFlagDraft] = []
            for flag in detected.flags:
                if flag.severity not in {RedFlagSeverity.HIGH, RedFlagSeverity.CRITICAL}:
                    output.append(flag)
                elif flag.citations and all(
                    item.valid
                    for item in validator.validate_all(
                        flag.citations,
                        expected_document_id=document_id,
                    )
                ):
                    eligible.append(flag)
                else:
                    output.append(
                        flag.model_copy(
                            update={
                                "status": RedFlagStatus.SUPPRESSED,
                                "verification_model": model,
                                "verification_reason": "Insufficient or invalid citation evidence",
                            }
                        )
                    )
            if eligible:
                eligible_json = json.dumps(
                    [flag.model_dump(mode="json", by_alias=True) for flag in eligible],
                    ensure_ascii=False,
                )
                prompt = (
                    f"Prompt version: {RED_FLAG_VERIFICATION_PROMPT_VERSION}. Verify only "
                    "HIGH/CRITICAL flags against their citations.\n"
                    f"flags={eligible_json}"
                )
                decisions = self.gateway.generate_structured(
                    model_alias=model,
                    prompt=prompt,
                    output_schema=RedFlagVerificationOutput,
                    timeout_seconds=step.timeout_seconds,
                    metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
                )
                by_id = {decision.flag_id: decision for decision in decisions.decisions}
                for flag in eligible:
                    decision = by_id.get(flag.flag_id)
                    verified = bool(decision and decision.verified and decision.evidence_sufficient)
                    output.append(
                        flag.model_copy(
                            update={
                                "status": (
                                    RedFlagStatus.VERIFIED if verified else RedFlagStatus.SUPPRESSED
                                ),
                                "verification_model": model,
                                "verification_reason": (
                                    decision.reason if decision else "Verifier omitted flag"
                                ),
                            }
                        )
                    )
            order = {flag.flag_id: index for index, flag in enumerate(detected.flags)}
            output.sort(key=lambda flag: order[flag.flag_id])
            return RedFlagOutput(flags=output)

        def question_handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
            flags = RedFlagOutput.model_validate(dependencies["verify-high-red-flags"]).flags
            public_flags = [flag for flag in flags if flag.status != RedFlagStatus.SUPPRESSED]
            if not public_flags:
                return CriticalQuestionOutput(questions=[])
            generated = self.gateway.generate_structured(
                model_alias=model,
                prompt=question_helper._generation_prompt(
                    public_flags,
                    self._evidence_chunks(chunks, public_flags),
                ),
                output_schema=CriticalQuestionOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            valid = [
                question
                for question in generated.questions[:5]
                if question_helper._question_valid(question, public_flags, document_id)
            ]
            return CriticalQuestionOutput(questions=valid)

        def question_verifier(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
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
                decisions = self.gateway.generate_structured(
                    model_alias=model,
                    prompt=question_helper._question_verification_prompt(
                        generated,
                        self._evidence_chunks(
                            chunks,
                            list(generated.questions),
                        ),
                    ),
                    output_schema=QuestionVerificationOutput,
                    timeout_seconds=step.timeout_seconds,
                    metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
                )
                by_index = {decision.question_index: decision for decision in decisions.decisions}
            verified = []
            for index, question in enumerate(generated.questions):
                if index not in complex_indices:
                    verified.append(
                        VerifiedCriticalQuestion(
                            draft=question,
                            verificationStatus=QuestionVerificationStatus.VERIFIED,
                        )
                    )
                else:
                    decision = by_index.get(index)
                    if decision and decision.verified and decision.evidence_sufficient:
                        verified.append(
                            VerifiedCriticalQuestion(
                                draft=question,
                                verificationStatus=QuestionVerificationStatus.VERIFIED,
                                verificationModel=model,
                            )
                        )
            return VerifiedCriticalQuestionOutput(questions=verified[:5])

        execution = WorkflowExecutor(self.session).execute(
            plan,
            {
                TaskType.DOCUMENT_SUMMARY: summary_handler,
                TaskType.ENTITY_RELATION_EXTRACTION: extract_handler,
                TaskType.ENTITY_NORMALIZATION: normalize_handler,
                TaskType.COMPLEX_RELATION_VERIFICATION: relation_handler,
                TaskType.RED_FLAG_DETECTION: flag_handler,
                TaskType.RED_FLAG_VERIFICATION: flag_verifier,
                TaskType.CRITICAL_QUESTION_GENERATION: question_handler,
                TaskType.CRITICAL_QUESTION_VERIFICATION: question_verifier,
            },
            persist_plan=persist_plan,
        )
        if execution.status == WorkflowStatus.FAILED:
            result = self._result(execution)
            WorkflowRepository(self.session).complete(
                execution.workflow_id,
                status=WorkflowStatus.FAILED,
                result=result.model_dump(mode="json", by_alias=True),
                error_message="; ".join(
                    step.error for step in execution.steps if step.error
                )
                or None,
            )
            self.session.commit()
            return result
        return self._persist_outputs(
            document_id,
            execution,
            validator=validator,
        )

    def _persist_outputs(
        self,
        document_id: str,
        execution: WorkflowExecutionResult,
        *,
        validator: CitationValidator,
    ) -> DocumentAnalysisResult:
        by_id = {step.step_id: step for step in execution.steps}
        citation_repo = CitationRepository(self.session)
        needs_review = False
        summary_id = None
        graph_view: KnowledgeGraphView | None = None

        summary_step = by_id["generate-summary"]
        if summary_step.status == StepStatus.COMPLETED and summary_step.output is not None:
            output = DocumentSummaryOutput.model_validate(summary_step.output)
            summary_status = (
                SummaryStatus.NEEDS_REVIEW if output.rejected_items else SummaryStatus.COMPLETED
            )
            needs_review |= summary_status == SummaryStatus.NEEDS_REVIEW
            repository = SummaryRepository(self.session)
            summary = repository.create_version(
                document_id=document_id,
                workflow_id=execution.workflow_id,
                model_name=summary_step.executor,
                prompt_version=SUMMARY_PROMPT_VERSION,
                status=summary_status,
                rejected_item_count=len(output.rejected_items),
            )
            summary_id = summary.id
            for index, draft in enumerate(output.items):
                item = repository.add_item(summary.id, draft, order_index=index)
                self._save_citations(
                    citation_repo,
                    validator,
                    draft.citations,
                    CitationOwnerType.SUMMARY_ITEM,
                    item.id,
                    document_id,
                )

        graph_step = by_id["verify-complex-relations"]
        node_mapping: dict[str, str] = {}
        edge_mapping: dict[str, str] = {}
        if graph_step.status == StepStatus.COMPLETED and graph_step.output is not None:
            graph = GraphExtractionOutput.model_validate(graph_step.output)
            graph_repository = KnowledgeGraphRepository(self.session)
            graph_validator = KnowledgeGraphService(
                self.session,
                gateway=self.gateway,
                planner=self.planner,
                chunk_reader=SnapshotDocumentChunkReader(
                    self.chunk_reader.list_chunks(document_id)
                ),
                citation_validator=validator,
            ).validator
            issues = graph_validator.validate(graph, document_id=document_id)
            invalid_nodes = {issue.element_id for issue in issues if issue.element_type == "NODE"}
            invalid_edges = {issue.element_id for issue in issues if issue.element_type == "EDGE"}
            nodes = [node for node in graph.nodes if node.node_id not in invalid_nodes]
            node_keys = {node.node_id for node in nodes}
            edges = [
                edge
                for edge in graph.edges
                if edge.edge_id not in invalid_edges
                and edge.source_node_id in node_keys
                and edge.target_node_id in node_keys
            ]
            graph_needs_review = bool(issues) or any(
                edge.verification_status == VerificationStatus.NEEDS_REVIEW for edge in edges
            )
            needs_review |= graph_needs_review
            version = graph_repository.create_version(
                document_id=document_id,
                workflow_id=execution.workflow_id,
                status=(
                    GraphVersionStatus.NEEDS_REVIEW
                    if graph_needs_review
                    else GraphVersionStatus.COMPLETED
                ),
                model_pipeline=[
                    by_id[key].executor
                    for key in (
                        "extract-entities-relations",
                        "normalize-graph",
                        "verify-complex-relations",
                    )
                ],
                validation_issues=[
                    issue.model_dump(mode="json", by_alias=True) for issue in issues
                ],
            )
            for draft in nodes:
                stored = graph_repository.add_node(version, draft)
                node_mapping[draft.node_id] = stored.id
                self._save_citations(
                    citation_repo,
                    validator,
                    draft.citations,
                    CitationOwnerType.KNOWLEDGE_NODE,
                    stored.id,
                    document_id,
                )
            for draft in edges:
                stored = graph_repository.add_edge(
                    version,
                    draft,
                    source_node_id=node_mapping[draft.source_node_id],
                    target_node_id=node_mapping[draft.target_node_id],
                )
                edge_mapping[draft.edge_id] = stored.id
                self._save_citations(
                    citation_repo,
                    validator,
                    draft.citations,
                    CitationOwnerType.KNOWLEDGE_EDGE,
                    stored.id,
                    document_id,
                )
            graph_view = SqlAlchemyKnowledgeGraphReader(self.session).get_version(version.id)

        stored_flags = []
        flags_step = by_id["verify-high-red-flags"]
        if (
            graph_view
            and flags_step.status == StepStatus.COMPLETED
            and flags_step.output is not None
        ):
            flag_repository = RedFlagRepository(self.session)
            output = RedFlagOutput.model_validate(flags_step.output)
            for raw in output.flags:
                mapped = raw.model_copy(
                    update={
                        "related_node_ids": [
                            node_mapping[node_id]
                            for node_id in raw.related_node_ids
                            if node_id in node_mapping
                        ],
                        "related_edge_ids": [
                            edge_mapping[edge_id]
                            for edge_id in raw.related_edge_ids
                            if edge_id in edge_mapping
                        ],
                    }
                )
                stored = flag_repository.add(
                    document_id=document_id,
                    graph_version_id=graph_view.version_id,
                    workflow_id=execution.workflow_id,
                    draft=mapped,
                )
                stored_flags.append(stored)
                self._save_citations(
                    citation_repo,
                    validator,
                    raw.citations,
                    CitationOwnerType.RED_FLAG,
                    stored.id,
                    document_id,
                )

        question_count = 0
        question_step = by_id["verify-critical-questions"]
        if question_step.status == StepStatus.COMPLETED and question_step.output is not None:
            question_repository = CriticalQuestionRepository(self.session)
            batch = VerifiedCriticalQuestionOutput.model_validate(question_step.output)
            flag_by_issue = {}
            for flag in stored_flags:
                if flag.status != RedFlagStatus.SUPPRESSED.value:
                    flag_by_issue.setdefault(flag.issue_type, flag.id)
            for verified in batch.questions[:5]:
                draft = verified.draft
                stored = question_repository.add(
                    document_id=document_id,
                    workflow_id=execution.workflow_id,
                    draft=draft,
                    verification_status=verified.verification_status,
                    verification_model=verified.verification_model,
                    red_flag_id=flag_by_issue.get(draft.issue_type.value),
                )
                self._save_citations(
                    citation_repo,
                    validator,
                    draft.citations,
                    CitationOwnerType.CRITICAL_QUESTION,
                    stored.id,
                    document_id,
                )
                question_count += 1

        status = WorkflowStatus.NEEDS_REVIEW if needs_review else execution.status
        self.session.flush()
        flags = SqlAlchemyRedFlagReader(self.session).list_for_document(document_id)
        result = DocumentAnalysisResult(
            workflowId=execution.workflow_id,
            status=status,
            summaryId=summary_id,
            graphVersionId=graph_view.version_id if graph_view else None,
            redFlagCount=len(flags),
            criticalQuestionCount=question_count,
            steps=[step.model_dump(mode="json", by_alias=True) for step in execution.steps],
        )
        WorkflowRepository(self.session).complete(
            execution.workflow_id,
            status=status,
            result=result.model_dump(mode="json", by_alias=True),
        )
        self.session.commit()
        return result

    @staticmethod
    def _chunk_batches(chunks: list[DocumentChunkContract]) -> list[list[DocumentChunkContract]]:
        batches: list[list[DocumentChunkContract]] = []
        current: list[DocumentChunkContract] = []
        current_tokens = 0
        for chunk in chunks:
            token_count = max(1, chunk.token_count)
            if current and (
                len(current) >= ANALYSIS_BATCH_MAX_CHUNKS
                or current_tokens + token_count > ANALYSIS_BATCH_MAX_TOKENS
            ):
                batches.append(current)
                current = []
                current_tokens = 0
            current.append(chunk)
            current_tokens += token_count
        if current:
            batches.append(current)
        return batches or [[]]

    @staticmethod
    def _evidence_chunks(
        chunks: list[DocumentChunkContract],
        artifacts: list[Any],
    ) -> list[DocumentChunkContract]:
        chunk_ids = {
            citation.chunk_id
            for artifact in artifacts
            for citation in getattr(artifact, "citations", [])
        }
        selected = [chunk for chunk in chunks if chunk.id in chunk_ids]
        return selected or chunks[:ANALYSIS_BATCH_MAX_CHUNKS]

    @staticmethod
    def _save_citations(
        repository: CitationRepository,
        validator: CitationValidator,
        citations: list,
        owner_type: CitationOwnerType,
        owner_id: str,
        document_id: str,
    ) -> None:
        for citation in citations:
            result = validator.validate(citation, expected_document_id=document_id)
            if result.valid:
                repository.add_validated(
                    result,
                    owner_type=owner_type,
                    owner_id=owner_id,
                )

    @staticmethod
    def _result(execution: WorkflowExecutionResult) -> DocumentAnalysisResult:
        return DocumentAnalysisResult(
            workflowId=execution.workflow_id,
            status=execution.status,
            steps=[step.model_dump(mode="json", by_alias=True) for step in execution.steps],
        )

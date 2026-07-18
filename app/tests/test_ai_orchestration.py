from __future__ import annotations

from collections import Counter
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.citations.schemas import CitationDraft
from app.citations.validator import CitationValidator
from app.common.contracts import DocumentChunkContract, SectionSearchFilters
from app.knowledge_graph.normalization import GraphDeduplicator, NodeNormalizer
from app.knowledge_graph.schemas import (
    EdgeType,
    GraphExtractionOutput,
    KnowledgeEdgeDraft,
    KnowledgeNodeDraft,
    NodeType,
)
from app.knowledge_graph.service import KnowledgeGraphService
from app.knowledge_graph.validator import KnowledgeGraphValidator
from app.model.chunking import DocumentChunk as StoredDocumentChunk
from app.model.documents import Document
from app.model.extraction import DocumentPage, PageBlock
from app.model.processing import ProcessingStatus
from app.model.workspaces import Workspace
from app.model_audit.models import ModelExecution
from app.model_gateway.errors import ModelRateLimitError, StructuredOutputError
from app.model_gateway.gateway import CallableModelGateway
from app.model_gateway.registry import build_default_registry
from app.model_gateway.router import ModelRouter
from app.model_gateway.schemas import RoutingRequest, TaskType
from app.orchestrator.executor import WorkflowExecutor
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.repository import WorkflowRepository
from app.orchestrator.schemas import (
    ExecutionPlan,
    ExecutionStep,
    StepStatus,
    WorkflowIntent,
)
from app.orchestrator.service import DocumentAnalysisOrchestrator
from app.red_flags.rules import RedFlagRuleEngine
from app.red_flags.schemas import (
    CriticalQuestionOutput,
    RedFlagDraft,
    RedFlagRule,
    RedFlagSeverity,
    RedFlagStatus,
)
from app.red_flags.verification import HighSeverityFlagVerifier
from app.summaries.repository import SummaryRepository
from app.summaries.schemas import DocumentSummaryOutput, SummaryStatus
from app.summaries.service import SummaryService


class FakeChunkReader:
    def __init__(self, chunks: list[DocumentChunkContract]) -> None:
        self.chunks = chunks
        self.by_id = {chunk.id: chunk for chunk in chunks}

    def list_chunks(self, document_id: str):
        return [chunk for chunk in self.chunks if chunk.document_id == document_id]

    def get_chunk(self, chunk_id: str):
        if chunk_id not in self.by_id:
            raise KeyError(chunk_id)
        return self.by_id[chunk_id]

    def search_chunks_by_section(self, document_id: str, filters: SectionSearchFilters):
        del filters
        return self.list_chunks(document_id)

    def get_page_blocks(self, document_id: str, page_index: int):
        del document_id, page_index
        return []

    def get_document_structure(self, document_id: str):
        del document_id
        return []


def chunk(document_id: str = "doc-a", chunk_id: str = "chunk-a") -> DocumentChunkContract:
    return DocumentChunkContract(
        id=chunk_id,
        documentId=document_id,
        chunkType="LEGAL_CLAUSE",
        content="Điều 7. Bộ Tài chính chủ trì và hoàn thành báo cáo trong 10 ngày.",
        normalizedContent="Điều 7. Bộ Tài chính chủ trì và hoàn thành báo cáo trong 10 ngày.",
        article="Điều 7",
        clause="Khoản 1",
        pdfPageStart=2,
        pdfPageEnd=2,
        startBlockId="block-a",
        endBlockId="block-b",
        boundingBoxes=[{"pageIndex": 2, "bbox": {"x1": 10, "y1": 20, "x2": 500, "y2": 80}}],
        ocrConfidence=0.96,
        tokenCount=20,
    )


def citation(document_id: str = "doc-a", quote: str = "Bộ Tài chính chủ trì") -> CitationDraft:
    return CitationDraft(
        documentId=document_id,
        chunkId="chunk-a",
        quote=quote,
        page=2,
        boundingBox={"x1": 20, "y1": 25, "x2": 300, "y2": 60},
        article="Điều 7",
        clause="Khoản 1",
        sourceConfidence=0.96,
    )


def validator() -> CitationValidator:
    return CitationValidator(
        FakeChunkReader([chunk()]),
        document_exists=lambda document_id: document_id == "doc-a",
    )


def plan(*, fallback: str | None = None, retries: int = 2) -> ExecutionPlan:
    return ExecutionPlan(
        intent=WorkflowIntent.DOCUMENT_SUMMARY,
        steps=[
            ExecutionStep(
                stepId="summary",
                taskType=TaskType.DOCUMENT_SUMMARY,
                executor="primary",
                reasonForSelection="test",
                timeoutSeconds=2,
                maxRetries=retries,
                fallbackModel=fallback,
                expectedOutputSchema="dict",
            )
        ],
    )


def test_model_routing_for_summary() -> None:
    decision = ModelRouter(build_default_registry()).route(
        RoutingRequest(taskType=TaskType.DOCUMENT_SUMMARY)
    )
    assert decision.primary_model == "DeepSeek-V4-Flash"
    assert decision.fallback_model == "GLM-5.1"


def test_model_routing_for_cross_document() -> None:
    decision = ModelRouter(build_default_registry()).route(
        RoutingRequest(taskType=TaskType.CROSS_DOCUMENT_ANALYSIS)
    )
    assert decision.primary_model == "GLM-5.2"


def test_private_policy_routes_to_private_reasoning_model() -> None:
    decision = ModelRouter(build_default_registry()).route(
        RoutingRequest(taskType=TaskType.DOCUMENT_SUMMARY, requirePrivate=True)
    )
    assert decision.primary_model == "gpt-oss-120b"


def test_retry_succeeds_on_third_attempt(session_factory: sessionmaker[Session]) -> None:
    calls = 0

    def handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
        nonlocal calls
        del step, model, dependencies
        calls += 1
        if calls < 3:
            raise TimeoutError("transient")
        return {"ok": True}

    with session_factory() as session:
        result = WorkflowExecutor(session).execute(
            plan(),
            {TaskType.DOCUMENT_SUMMARY: handler},
        )
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[0].attempts == 3


def test_one_fallback_after_retries(session_factory: sessionmaker[Session]) -> None:
    calls: list[str] = []

    def handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
        del step, dependencies
        calls.append(model)
        if model == "primary":
            raise RuntimeError("primary failed")
        return {"model": model}

    with session_factory() as session:
        result = WorkflowExecutor(session).execute(
            plan(fallback="fallback"),
            {TaskType.DOCUMENT_SUMMARY: handler},
        )
        assert calls == ["primary", "primary", "primary", "fallback"]
        assert result.steps[0].used_fallback is True


def test_rate_limit_fails_without_retry_or_fallback(
    session_factory: sessionmaker[Session],
) -> None:
    calls: list[str] = []

    def handler(step: ExecutionStep, model: str, dependencies: dict[str, Any]):
        del step, dependencies
        calls.append(model)
        raise ModelRateLimitError(model)

    with session_factory() as session:
        result = WorkflowExecutor(session).execute(
            plan(fallback="fallback"),
            {TaskType.DOCUMENT_SUMMARY: handler},
        )

    assert calls == ["primary"]
    assert result.steps[0].attempts == 1
    assert result.steps[0].status == StepStatus.FAILED


def test_analysis_batches_chunks_by_count_and_token_budget() -> None:
    chunks = [chunk(chunk_id=f"chunk-{index}") for index in range(25)]
    batches = DocumentAnalysisOrchestrator._chunk_batches(chunks)

    assert [len(batch) for batch in batches] == [12, 12, 1]


def test_ai_prompt_payload_omits_bounding_boxes() -> None:
    summary_prompt = SummaryService._summary_prompt("doc-a", [chunk()], "test")
    graph_payload = KnowledgeGraphService._chunks_payload([chunk()])

    assert "boundingBoxes" not in summary_prompt
    assert "boundingBoxes" not in graph_payload[0]


def test_structured_output_validation_rejects_invalid_json() -> None:
    gateway = CallableModelGateway(lambda operation, model, payload: "not-json")
    with pytest.raises(StructuredOutputError):
        gateway.generate_structured(
            model_alias="DeepSeek-V4-Flash",
            prompt="summary",
            output_schema=DocumentSummaryOutput,
        )


def test_valid_citation() -> None:
    result = validator().validate(citation(), expected_document_id="doc-a")
    assert result.valid is True


def test_citation_from_wrong_document_is_rejected() -> None:
    result = validator().validate(citation("doc-b"), expected_document_id="doc-a")
    codes = {issue.code for issue in result.issues}
    assert "CROSS_DOCUMENT_CITATION" in codes
    assert "CHUNK_DOCUMENT_MISMATCH" in codes


def test_quote_not_present_is_rejected() -> None:
    result = validator().validate(citation(quote="Nội dung không tồn tại"))
    assert "QUOTE_NOT_FOUND" in {issue.code for issue in result.issues}


def _document(session: Session) -> Document:
    workspace = Workspace(name="AI tests")
    session.add(workspace)
    session.flush()
    document = Document(
        workspace_id=workspace.id,
        display_name="Văn bản",
        original_filename="van-ban.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1,
        checksum="a" * 64,
        status=ProcessingStatus.COMPLETED,
    )
    session.add(document)
    session.flush()
    return document


def _stored_chunk(session: Session, document: Document) -> DocumentChunkContract:
    page = DocumentPage(
        document_id=document.id,
        page_index=2,
        width=600,
        height=800,
        rotation=0,
        has_text_layer=True,
        image_only=False,
        needs_ocr=False,
        extracted_text=chunk(document.id).content,
    )
    block = PageBlock(
        id="block-ai-test",
        document_id=document.id,
        page=page,
        order_index=0,
        text=chunk(document.id).content,
        normalized_text=chunk(document.id).content,
        bbox={"x1": 10, "y1": 20, "x2": 500, "y2": 80},
        confidence=0.96,
        source="TEXT_LAYER",
    )
    session.add_all([page, block])
    session.flush()
    stored = StoredDocumentChunk(
        id="chunk-a",
        document_id=document.id,
        order_index=0,
        chunk_type="LEGAL_CLAUSE",
        content=chunk(document.id).content,
        normalized_content=chunk(document.id).normalized_content,
        article="Điều 7",
        clause="Khoản 1",
        pdf_page_start=2,
        pdf_page_end=2,
        start_block_id=block.id,
        end_block_id=block.id,
        bounding_boxes=chunk(document.id).bounding_boxes,
        ocr_confidence=0.96,
        token_count=20,
    )
    session.add(stored)
    session.flush()
    return chunk(document.id)


def test_summary_versioning(session_factory: sessionmaker[Session]) -> None:
    planner = ExecutionPlanner(ModelRouter(build_default_registry()))
    with session_factory() as session:
        document = _document(session)
        workflow_repository = WorkflowRepository(session)
        first_workflow = workflow_repository.create(planner.summary_plan(document.id))
        repository = SummaryRepository(session)
        first = repository.create_version(
            document_id=document.id,
            workflow_id=first_workflow.id,
            model_name="DeepSeek-V4-Flash",
            prompt_version="v1",
            status=SummaryStatus.COMPLETED,
        )
        second_workflow = workflow_repository.create(planner.summary_plan(document.id))
        second = repository.create_version(
            document_id=document.id,
            workflow_id=second_workflow.id,
            model_name="DeepSeek-V4-Flash",
            prompt_version="v2",
            status=SummaryStatus.COMPLETED,
        )
        session.commit()
        assert (first.version, second.version) == (1, 2)
        assert first.is_current is False
        assert second.is_current is True
        assert first.status == SummaryStatus.SUPERSEDED.value


def test_summary_service_persists_only_valid_cited_item(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        document = _document(session)
        source_chunk = _stored_chunk(session, document)
        source_citation = citation(document.id)
        gateway = CallableModelGateway(
            lambda operation, model, payload: {
                "items": [
                    {
                        "category": "RESPONSIBILITY",
                        "title": "Trách nhiệm của Bộ Tài chính",
                        "content": "Bộ Tài chính chủ trì.",
                        "importance": "HIGH",
                        "confidence": 0.94,
                        "citations": [source_citation.model_dump(mode="json", by_alias=True)],
                    }
                ]
            }
        )
        source_reader = FakeChunkReader([source_chunk])
        result = SummaryService(
            session,
            gateway=gateway,
            planner=ExecutionPlanner(ModelRouter(build_default_registry())),
            chunk_reader=source_reader,
            citation_validator=CitationValidator(
                source_reader,
                document_exists=lambda candidate: candidate == document.id,
            ),
        ).generate(document.id)
        assert result.summary is not None
        assert result.summary.status == SummaryStatus.COMPLETED
        assert len(result.summary.items) == 1
        assert len(result.summary.items[0].citations) == 1


def test_summary_rejects_item_after_two_failed_citation_repairs(
    session_factory: sessionmaker[Session],
) -> None:
    calls = 0
    with session_factory() as session:
        document = _document(session)
        source_chunk = _stored_chunk(session, document)
        invalid_item = {
            "category": "RESPONSIBILITY",
            "title": "Nội dung không có nguồn",
            "content": "Một kết luận không có trong văn bản.",
            "importance": "HIGH",
            "confidence": 0.5,
            "citations": [
                citation(document.id, "quote không tồn tại").model_dump(mode="json", by_alias=True)
            ],
        }

        def model_handler(operation: str, model: str, payload: dict[str, Any]):
            nonlocal calls
            del operation, model
            calls += 1
            if payload["metadata"].get("operation") == "citation-repair":
                return {"item": invalid_item}
            return {"items": [invalid_item]}

        source_reader = FakeChunkReader([source_chunk])
        result = SummaryService(
            session,
            gateway=CallableModelGateway(model_handler),
            planner=ExecutionPlanner(ModelRouter(build_default_registry())),
            chunk_reader=source_reader,
            citation_validator=CitationValidator(
                source_reader,
                document_exists=lambda candidate: candidate == document.id,
            ),
        ).generate(document.id)
        assert calls == 3
        assert result.summary is not None
        assert result.summary.status == SummaryStatus.NEEDS_REVIEW
        assert result.summary.items == []


def test_knowledge_graph_service_runs_extraction_normalization_and_dedup(
    session_factory: sessionmaker[Session],
) -> None:
    graph_payload = {
        "nodes": [
            {
                "nodeId": "agency",
                "type": "AGENCY",
                "name": "Bộ Tài chính",
                "confidence": 0.95,
            },
            {
                "nodeId": "task",
                "type": "TASK",
                "name": "Lập báo cáo",
                "confidence": 0.9,
            },
        ],
        "edges": [
            {
                "edgeId": "lead",
                "sourceNodeId": "agency",
                "targetNodeId": "task",
                "type": "LEADS",
                "confidence": 0.9,
            }
        ],
    }
    with session_factory() as session:
        document = _document(session)
        source_reader = FakeChunkReader([chunk(document.id)])
        result = KnowledgeGraphService(
            session,
            gateway=CallableModelGateway(lambda operation, model, payload: graph_payload),
            planner=ExecutionPlanner(ModelRouter(build_default_registry())),
            chunk_reader=source_reader,
            citation_validator=CitationValidator(
                source_reader,
                document_exists=lambda candidate: candidate == document.id,
            ),
        ).generate(document.id)
        assert result.graph is not None
        assert len(result.graph.nodes) == 2
        assert len(result.graph.edges) == 1


def test_entity_and_relation_extraction_schema() -> None:
    output = GraphExtractionOutput(
        nodes=[
            KnowledgeNodeDraft(
                nodeId="agency",
                type=NodeType.AGENCY,
                name="Bộ Tài chính",
                confidence=0.95,
            ),
            KnowledgeNodeDraft(
                nodeId="task",
                type=NodeType.TASK,
                name="Lập báo cáo",
                confidence=0.9,
            ),
        ],
        edges=[
            KnowledgeEdgeDraft(
                edgeId="lead",
                sourceNodeId="agency",
                targetNodeId="task",
                type=EdgeType.LEADS,
                confidence=0.9,
            )
        ],
    )
    assert output.edges[0].type == EdgeType.LEADS


def test_node_normalization_is_accent_and_case_stable() -> None:
    normalizer = NodeNormalizer()
    first = normalizer.normalize_node(
        KnowledgeNodeDraft(
            nodeId="a", type=NodeType.AGENCY, name="BỘ TÀI CHÍNH (BTC)", confidence=0.9
        )
    )
    second = normalizer.normalize_node(
        KnowledgeNodeDraft(nodeId="b", type=NodeType.AGENCY, name="Bo Tai Chinh", confidence=0.8)
    )
    assert first.normalized_key == second.normalized_key


def test_rule_based_node_deduplication() -> None:
    normalizer = NodeNormalizer()
    graph = normalizer.normalize(
        GraphExtractionOutput(
            nodes=[
                KnowledgeNodeDraft(
                    nodeId="a", type=NodeType.AGENCY, name="Bộ Tài chính", confidence=0.8
                ),
                KnowledgeNodeDraft(
                    nodeId="b", type=NodeType.AGENCY, name="Bo Tai Chinh", confidence=0.9
                ),
            ]
        )
    )
    deduplicated = GraphDeduplicator().deduplicate(graph)
    assert len(deduplicated.nodes) == 1
    assert deduplicated.nodes[0].confidence == 0.9


def test_edge_validation_rejects_missing_endpoint() -> None:
    graph = GraphExtractionOutput(
        nodes=[KnowledgeNodeDraft(nodeId="a", type=NodeType.AGENCY, name="Bộ A", confidence=0.9)],
        edges=[
            KnowledgeEdgeDraft(
                edgeId="broken",
                sourceNodeId="a",
                targetNodeId="missing",
                type=EdgeType.LEADS,
                confidence=0.9,
            )
        ],
    )
    issues = KnowledgeGraphValidator(validator()).validate(graph, document_id="doc-a")
    assert "MISSING_TARGET_NODE" in {issue.code for issue in issues}


def _node(node_id: str, node_type: NodeType, name: str, **kwargs: Any):
    return KnowledgeNodeDraft(
        nodeId=node_id,
        type=node_type,
        name=name,
        confidence=kwargs.pop("confidence", 0.9),
        **kwargs,
    )


def _rule_codes(graph: GraphExtractionOutput) -> Counter:
    return Counter(flag.issue_type for flag in RedFlagRuleEngine().evaluate(graph))


def test_missing_lead_agency_rule() -> None:
    graph = GraphExtractionOutput(nodes=[_node("task", NodeType.TASK, "Nhiệm vụ A")])
    assert _rule_codes(graph)[RedFlagRule.MISSING_LEAD_AGENCY] == 1


def test_missing_funding_source_rule() -> None:
    graph = GraphExtractionOutput(
        nodes=[_node("budget", NodeType.BUDGET, "Kinh phí", properties={"amount": 10})]
    )
    assert _rule_codes(graph)[RedFlagRule.MISSING_FUNDING_SOURCE] == 1


def test_deadline_without_output_rule() -> None:
    graph = GraphExtractionOutput(
        nodes=[
            _node("task", NodeType.TASK, "Nhiệm vụ A"),
            _node("deadline", NodeType.DEADLINE, "10 ngày"),
        ],
        edges=[
            KnowledgeEdgeDraft(
                edgeId="deadline-edge",
                sourceNodeId="task",
                targetNodeId="deadline",
                type=EdgeType.HAS_DEADLINE,
                confidence=0.9,
            )
        ],
    )
    assert _rule_codes(graph)[RedFlagRule.DEADLINE_WITHOUT_OUTPUT] == 1


def test_broken_legal_reference_rule() -> None:
    graph = GraphExtractionOutput(
        nodes=[
            _node(
                "reference",
                NodeType.LEGAL_REFERENCE,
                "Điều 99",
                properties={"resolved": False},
            )
        ]
    )
    assert _rule_codes(graph)[RedFlagRule.BROKEN_LEGAL_REFERENCE] == 1


def test_high_flag_requires_and_records_reasoning_verification() -> None:
    flag = RedFlagDraft(
        issueType=RedFlagRule.MISSING_LEAD_AGENCY,
        severity=RedFlagSeverity.HIGH,
        title="Thiếu chủ trì",
        description="Nhiệm vụ chưa có cơ quan chủ trì",
        citations=[citation()],
    )

    def handler(operation: str, model: str, payload: dict[str, Any]):
        del operation, model, payload
        return {
            "decisions": [
                {
                    "flagId": flag.flag_id,
                    "verified": True,
                    "evidenceSufficient": True,
                    "reason": "Nguồn xác nhận nhiệm vụ nhưng không nêu cơ quan chủ trì",
                }
            ]
        }

    result = HighSeverityFlagVerifier(
        CallableModelGateway(handler),
        validator(),
    ).verify(
        [flag],
        document_id="doc-a",
        model_alias="GLM-5.2",
        timeout_seconds=10,
        workflow_id="workflow",
        step_id="verify",
    )
    assert result.flags[0].status == RedFlagStatus.VERIFIED
    assert result.flags[0].verification_model == "GLM-5.2"


def test_critical_question_generation_has_valid_citation() -> None:
    gateway = CallableModelGateway(
        lambda operation, model, payload: {
            "questions": [
                {
                    "question": "Bộ Tài chính sẽ chủ trì nhiệm vụ lập báo cáo theo cơ chế nào?",
                    "reason": "Điều 7 nêu nhiệm vụ nhưng cơ chế chủ trì cần được làm rõ.",
                    "issueType": "MISSING_LEAD_AGENCY",
                    "severity": "HIGH",
                    "relatedSubject": "Bộ Tài chính",
                    "sourceLocation": "Điều 7, khoản 1, trang 2",
                    "riskIfUnresolved": "Không xác định được đầu mối chịu trách nhiệm.",
                    "citations": [citation().model_dump(mode="json", by_alias=True)],
                }
            ]
        }
    )
    output = gateway.generate_structured(
        model_alias="DeepSeek-V4-Flash",
        prompt="generate",
        output_schema=CriticalQuestionOutput,
    )
    assert len(output.questions) == 1
    assert validator().validate(output.questions[0].citations[0]).valid


def test_workflow_execution_is_audited(session_factory: sessionmaker[Session]) -> None:
    workflow_plan = plan(retries=0)
    with session_factory() as session:
        WorkflowExecutor(session).execute(
            workflow_plan,
            {TaskType.DOCUMENT_SUMMARY: lambda step, model, deps: {"ok": True}},
        )
        executions = list(
            session.scalars(
                select(ModelExecution).where(
                    ModelExecution.workflow_id == workflow_plan.workflow_id
                )
            )
        )
        assert len(executions) == 1
        assert executions[0].model_alias == "primary"
        assert executions[0].status == StepStatus.COMPLETED.value
        view = WorkflowRepository(session).view(workflow_plan.workflow_id)
        assert view is not None
        assert view.model_executions[0].attempt_number == 1

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.citations.repository import CitationRepository
from app.citations.schemas import CitationOwnerType
from app.citations.validator import CitationValidator
from app.documents.interfaces import DocumentChunkContract, DocumentChunkReader
from app.knowledge_graph.normalization import GraphDeduplicator, NodeNormalizer
from app.knowledge_graph.prompts import (
    GRAPH_EXTRACTION_PROMPT_VERSION,
    GRAPH_NORMALIZATION_PROMPT_VERSION,
    RELATION_VERIFICATION_PROMPT_VERSION,
)
from app.knowledge_graph.reader import SqlAlchemyKnowledgeGraphReader
from app.knowledge_graph.repository import KnowledgeGraphRepository
from app.knowledge_graph.schemas import (
    EdgeType,
    GraphExtractionOutput,
    GraphVersionStatus,
    KnowledgeEdgeDraft,
    KnowledgeGraphGenerationResult,
    RelationVerificationOutput,
    VerificationStatus,
)
from app.knowledge_graph.validator import KnowledgeGraphValidator
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.schemas import TaskType
from app.orchestrator.executor import WorkflowExecutor
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.schemas import ExecutionStep, StepStatus

COMPLEX_EDGE_TYPES = {
    EdgeType.ASSIGNS_RESPONSIBILITY,
    EdgeType.GRANTS_AUTHORITY,
    EdgeType.HAS_BUDGET,
    EdgeType.HAS_DEADLINE,
    EdgeType.REFERENCES,
    EdgeType.REPEALS,
    EdgeType.REPLACES,
}


class KnowledgeGraphService:
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
        self.repository = KnowledgeGraphRepository(session)
        self.citation_repository = CitationRepository(session)
        self.normalizer = NodeNormalizer()
        self.deduplicator = GraphDeduplicator()
        self.validator = KnowledgeGraphValidator(citation_validator)

    def generate(
        self,
        document_id: str,
        *,
        private: bool = False,
    ) -> KnowledgeGraphGenerationResult:
        chunks = self.chunk_reader.list_chunks(document_id)
        plan = self.planner.knowledge_graph_plan(document_id, private=private)

        def extract(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> GraphExtractionOutput:
            del dependencies
            return self.gateway.generate_structured(
                model_alias=model_alias,
                prompt=self._extraction_prompt(document_id, chunks),
                output_schema=GraphExtractionOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )

        def normalize(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> GraphExtractionOutput:
            extracted = GraphExtractionOutput.model_validate(
                dependencies["extract-entities-relations"]
            )
            normalized_by_model = self.gateway.generate_structured(
                model_alias=model_alias,
                prompt=self._normalization_prompt(extracted),
                output_schema=GraphExtractionOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            return self.deduplicator.deduplicate(self.normalizer.normalize(normalized_by_model))

        def verify(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> GraphExtractionOutput:
            graph = GraphExtractionOutput.model_validate(dependencies["normalize-graph"])
            complex_edges = self._complex_edges(graph)
            if not complex_edges:
                return graph
            verification = self.gateway.generate_structured(
                model_alias=model_alias,
                prompt=self._verification_prompt(graph, complex_edges, chunks),
                output_schema=RelationVerificationOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            by_id = {item.edge_id: item for item in verification.verifications}
            updated_edges = []
            complex_ids = {edge.edge_id for edge in complex_edges}
            for edge in graph.edges:
                if edge.edge_id not in complex_ids:
                    updated_edges.append(edge)
                    continue
                decision = by_id.get(edge.edge_id)
                status = (
                    VerificationStatus.VERIFIED
                    if decision and decision.verified and decision.evidence_sufficient
                    else VerificationStatus.NEEDS_REVIEW
                )
                updated_edges.append(edge.model_copy(update={"verification_status": status}))
            return GraphExtractionOutput(nodes=graph.nodes, edges=updated_edges)

        result = WorkflowExecutor(self.session).execute(
            plan,
            {
                TaskType.ENTITY_RELATION_EXTRACTION: extract,
                TaskType.ENTITY_NORMALIZATION: normalize,
                TaskType.COMPLEX_RELATION_VERIFICATION: verify,
            },
        )
        final_step = result.steps[-1]
        if final_step.status != StepStatus.COMPLETED or final_step.output is None:
            return KnowledgeGraphGenerationResult(workflowId=plan.workflow_id, graph=None)
        graph = GraphExtractionOutput.model_validate(final_step.output)
        issues = self.validator.validate(graph, document_id=document_id)
        invalid_nodes = {issue.element_id for issue in issues if issue.element_type == "NODE"}
        invalid_edges = {issue.element_id for issue in issues if issue.element_type == "EDGE"}
        kept_nodes = [node for node in graph.nodes if node.node_id not in invalid_nodes]
        kept_node_ids = {node.node_id for node in kept_nodes}
        kept_edges = [
            edge
            for edge in graph.edges
            if edge.edge_id not in invalid_edges
            and edge.source_node_id in kept_node_ids
            and edge.target_node_id in kept_node_ids
        ]
        if any(edge.verification_status == VerificationStatus.NEEDS_REVIEW for edge in kept_edges):
            status = GraphVersionStatus.NEEDS_REVIEW
        else:
            status = GraphVersionStatus.NEEDS_REVIEW if issues else GraphVersionStatus.COMPLETED
        version = self.repository.create_version(
            document_id=document_id,
            workflow_id=plan.workflow_id,
            status=status,
            model_pipeline=[step.executor for step in result.steps],
            validation_issues=[issue.model_dump(mode="json", by_alias=True) for issue in issues],
        )
        node_mapping = {}
        for node in kept_nodes:
            stored = self.repository.add_node(version, node)
            node_mapping[node.node_id] = stored.id
            self._persist_citations(
                node.citations,
                owner_type=CitationOwnerType.KNOWLEDGE_NODE,
                owner_id=stored.id,
                document_id=document_id,
            )
        for edge in kept_edges:
            stored = self.repository.add_edge(
                version,
                edge,
                source_node_id=node_mapping[edge.source_node_id],
                target_node_id=node_mapping[edge.target_node_id],
            )
            self._persist_citations(
                edge.citations,
                owner_type=CitationOwnerType.KNOWLEDGE_EDGE,
                owner_id=stored.id,
                document_id=document_id,
            )
        self.session.commit()
        view = SqlAlchemyKnowledgeGraphReader(self.session).get_version(version.id)
        return KnowledgeGraphGenerationResult(workflowId=plan.workflow_id, graph=view)

    def _persist_citations(
        self,
        citations: list,
        *,
        owner_type: CitationOwnerType,
        owner_id: str,
        document_id: str,
    ) -> None:
        for citation in citations:
            result = self.citation_validator.validate(
                citation,
                expected_document_id=document_id,
            )
            if result.valid:
                self.citation_repository.add_validated(
                    result,
                    owner_type=owner_type,
                    owner_id=owner_id,
                )

    @staticmethod
    def _complex_edges(graph: GraphExtractionOutput) -> list[KnowledgeEdgeDraft]:
        candidates = [edge for edge in graph.edges if edge.type in COMPLEX_EDGE_TYPES]
        target_type_counts: dict[tuple[str, EdgeType], int] = {}
        for edge in graph.edges:
            key = edge.target_node_id, edge.type
            target_type_counts[key] = target_type_counts.get(key, 0) + 1
        conflicting_ids = {
            edge.edge_id
            for edge in graph.edges
            if target_type_counts[(edge.target_node_id, edge.type)] > 1
        }
        return [
            edge for edge in graph.edges if edge in candidates or edge.edge_id in conflicting_ids
        ]

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
                "sourceConfidence": chunk.ocr_confidence,
            }
            for chunk in chunks
        ]

    def _extraction_prompt(
        self,
        document_id: str,
        chunks: list[DocumentChunkContract],
    ) -> str:
        schema_json = json.dumps(
            GraphExtractionOutput.model_json_schema(by_alias=True),
            ensure_ascii=False,
        )
        return (
            f"Prompt version: {GRAPH_EXTRACTION_PROMPT_VERSION}. Trích xuất entity/relation "
            "pháp lý sơ bộ. Chỉ dùng node/edge types trong JSON schema. Node/edge HIGH hoặc "
            "CRITICAL phải có citation đúng document/chunk/quote/page. Không tạo quan hệ thiếu "
            "đầu mút.\n"
            f"documentId={document_id}\n"
            f"schema={schema_json}\n"
            f"chunks={json.dumps(self._chunks_payload(chunks), ensure_ascii=False)}"
        )

    @staticmethod
    def _normalization_prompt(graph: GraphExtractionOutput) -> str:
        return (
            f"Prompt version: {GRAPH_NORMALIZATION_PROMPT_VERSION}. Chuẩn hóa type, tên, "
            "canonicalName và metadata; giữ nguyên nodeId/edgeId và citation, không thêm fact. "
            "Trả đúng GraphExtractionOutput.\n"
            f"graph={graph.model_dump_json(by_alias=True)}"
        )

    def _verification_prompt(
        self,
        graph: GraphExtractionOutput,
        edges: list[KnowledgeEdgeDraft],
        chunks: list[DocumentChunkContract],
    ) -> str:
        nodes_json = json.dumps(
            [node.model_dump(mode="json", by_alias=True) for node in graph.nodes],
            ensure_ascii=False,
        )
        edges_json = json.dumps(
            [edge.model_dump(mode="json", by_alias=True) for edge in edges],
            ensure_ascii=False,
        )
        return (
            f"Prompt version: {RELATION_VERIFICATION_PROMPT_VERSION}. Chỉ kiểm chứng các "
            "relation phức tạp/mâu thuẫn được liệt kê. verified=true chỉ khi citation và "
            "nội dung nguồn đủ chứng minh đúng source, target và relation.\n"
            f"nodes={nodes_json}\n"
            f"edges={edges_json}\n"
            f"chunks={json.dumps(self._chunks_payload(chunks), ensure_ascii=False)}"
        )

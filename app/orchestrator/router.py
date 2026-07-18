from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.chunking.reader import SqlAlchemyDocumentChunkReader
from app.common.contracts import APIModel, ApiSuccessResponse
from app.config.database import get_db
from app.exceptions import NotFoundError
from app.knowledge_graph.reader import SqlAlchemyKnowledgeGraphReader
from app.knowledge_graph.schemas import KnowledgeGraphGenerationResult, KnowledgeGraphView
from app.knowledge_graph.service import KnowledgeGraphService
from app.model.documents import Document
from app.model_gateway.gateway import MetadataModelGateway, ModelGateway
from app.orchestrator.dependencies import (
    build_citation_validator,
    get_execution_planner,
    get_model_gateway,
)
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.repository import WorkflowRepository
from app.orchestrator.schemas import WorkflowView
from app.orchestrator.service import DocumentAnalysisOrchestrator, DocumentAnalysisResult
from app.red_flags.reader import SqlAlchemyRedFlagReader
from app.red_flags.schemas import (
    CriticalQuestionGenerationResult,
    CriticalQuestionView,
    RedFlagView,
)
from app.red_flags.service import CriticalQuestionService, RedFlagService
from app.summaries.reader import SqlAlchemySummaryReader
from app.summaries.schemas import (
    DocumentSummaryView,
    SummaryGenerationResult,
)
from app.summaries.service import SummaryService

router = APIRouter(tags=["AI Orchestration"])


class GenerationRequest(APIModel):
    private_processing: bool = False


def _ensure_document(session: Session, document_id: str) -> Document:
    document = session.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise NotFoundError("DOCUMENT", document_id)
    return document


def _request_gateway(gateway: ModelGateway, *, private: bool) -> ModelGateway:
    return MetadataModelGateway(gateway, {"private": private})


@router.post(
    "/documents/{document_id}/analysis",
    response_model=ApiSuccessResponse[DocumentAnalysisResult],
    status_code=status.HTTP_201_CREATED,
)
def analyze_document(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    planner: Annotated[ExecutionPlanner, Depends(get_execution_planner)],
    body: GenerationRequest | None = None,
) -> ApiSuccessResponse[DocumentAnalysisResult]:
    _ensure_document(session, document_id)
    private = body.private_processing if body else False
    chunk_reader = SqlAlchemyDocumentChunkReader(session)
    result = DocumentAnalysisOrchestrator(
        session,
        gateway=_request_gateway(gateway, private=private),
        planner=planner,
        chunk_reader=chunk_reader,
        citation_validator=build_citation_validator(session),
    ).analyze(
        document_id,
        private=private,
    )
    return ApiSuccessResponse(data=result, message="Document analysis workflow executed")


@router.get(
    "/workflows/{workflow_id}",
    response_model=ApiSuccessResponse[WorkflowView],
)
def get_workflow(
    workflow_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[WorkflowView]:
    workflow = WorkflowRepository(session).view(workflow_id)
    if workflow is None:
        raise NotFoundError("WORKFLOW", workflow_id)
    return ApiSuccessResponse(data=workflow)


@router.post(
    "/documents/{document_id}/summaries/generate",
    response_model=ApiSuccessResponse[SummaryGenerationResult],
    status_code=status.HTTP_201_CREATED,
)
def generate_summary(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    planner: Annotated[ExecutionPlanner, Depends(get_execution_planner)],
    body: GenerationRequest | None = None,
) -> ApiSuccessResponse[SummaryGenerationResult]:
    _ensure_document(session, document_id)
    private = body.private_processing if body else False
    reader = SqlAlchemyDocumentChunkReader(session)
    result = SummaryService(
        session,
        gateway=_request_gateway(gateway, private=private),
        planner=planner,
        chunk_reader=reader,
        citation_validator=build_citation_validator(session),
    ).generate(
        document_id,
        private=private,
    )
    return ApiSuccessResponse(data=result, message="Summary generation workflow executed")


@router.get(
    "/documents/{document_id}/summaries",
    response_model=ApiSuccessResponse[list[DocumentSummaryView]],
)
def list_summaries(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[list[DocumentSummaryView]]:
    _ensure_document(session, document_id)
    return ApiSuccessResponse(data=SqlAlchemySummaryReader(session).list_for_document(document_id))


@router.get(
    "/summaries/{summary_id}",
    response_model=ApiSuccessResponse[DocumentSummaryView],
)
def get_summary(
    summary_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[DocumentSummaryView]:
    summary = SqlAlchemySummaryReader(session).get_summary(summary_id)
    if summary is None:
        raise NotFoundError("SUMMARY", summary_id)
    return ApiSuccessResponse(data=summary)


@router.post(
    "/documents/{document_id}/knowledge-graph/generate",
    response_model=ApiSuccessResponse[KnowledgeGraphGenerationResult],
    status_code=status.HTTP_201_CREATED,
)
def generate_knowledge_graph(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    planner: Annotated[ExecutionPlanner, Depends(get_execution_planner)],
    body: GenerationRequest | None = None,
) -> ApiSuccessResponse[KnowledgeGraphGenerationResult]:
    _ensure_document(session, document_id)
    reader = SqlAlchemyDocumentChunkReader(session)
    validator = build_citation_validator(session)
    private = body.private_processing if body else False
    result = KnowledgeGraphService(
        session,
        gateway=_request_gateway(gateway, private=private),
        planner=planner,
        chunk_reader=reader,
        citation_validator=validator,
    ).generate(document_id, private=private)
    if result.graph is not None:
        RedFlagService(
            session,
            gateway=_request_gateway(gateway, private=private),
            planner=planner,
            citation_validator=validator,
        ).evaluate(
            document_id,
            private=private,
            graph=result.graph,
        )
    return ApiSuccessResponse(data=result, message="Knowledge graph workflow executed")


@router.get(
    "/documents/{document_id}/knowledge-graph",
    response_model=ApiSuccessResponse[KnowledgeGraphView],
)
def get_knowledge_graph(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[KnowledgeGraphView]:
    _ensure_document(session, document_id)
    graph = SqlAlchemyKnowledgeGraphReader(session).get_graph(document_id)
    if graph is None:
        raise NotFoundError("KNOWLEDGE_GRAPH", document_id)
    return ApiSuccessResponse(data=graph)


@router.get(
    "/documents/{document_id}/red-flags",
    response_model=ApiSuccessResponse[list[RedFlagView]],
)
def get_red_flags(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
    include_suppressed: bool = False,
) -> ApiSuccessResponse[list[RedFlagView]]:
    _ensure_document(session, document_id)
    return ApiSuccessResponse(
        data=SqlAlchemyRedFlagReader(session).list_for_document(
            document_id,
            include_suppressed=include_suppressed,
        )
    )


@router.post(
    "/documents/{document_id}/critical-questions/generate",
    response_model=ApiSuccessResponse[CriticalQuestionGenerationResult],
    status_code=status.HTTP_201_CREATED,
)
def generate_critical_questions(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    planner: Annotated[ExecutionPlanner, Depends(get_execution_planner)],
    body: GenerationRequest | None = None,
) -> ApiSuccessResponse[CriticalQuestionGenerationResult]:
    _ensure_document(session, document_id)
    private = body.private_processing if body else False
    reader = SqlAlchemyDocumentChunkReader(session)
    result = CriticalQuestionService(
        session,
        gateway=_request_gateway(gateway, private=private),
        planner=planner,
        chunk_reader=reader,
        citation_validator=build_citation_validator(session),
    ).generate(
        document_id,
        private=private,
    )
    return ApiSuccessResponse(data=result, message="Critical questions workflow executed")


@router.get(
    "/documents/{document_id}/critical-questions",
    response_model=ApiSuccessResponse[list[CriticalQuestionView]],
)
def get_critical_questions(
    document_id: Annotated[str, Path(min_length=1)],
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    planner: Annotated[ExecutionPlanner, Depends(get_execution_planner)],
) -> ApiSuccessResponse[list[CriticalQuestionView]]:
    _ensure_document(session, document_id)
    service = CriticalQuestionService(
        session,
        gateway=gateway,
        planner=planner,
        chunk_reader=SqlAlchemyDocumentChunkReader(session),
        citation_validator=build_citation_validator(session),
    )
    return ApiSuccessResponse(data=service.list_for_document(document_id))

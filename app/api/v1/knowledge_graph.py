from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.api.v1.documents import get_visible_document
from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.core.permissions import Permission
from app.dependencies.permissions import require_permission
from app.knowledge_graph.schemas import KnowledgeGraphGenerationResult, KnowledgeGraphView
from app.model.users import User
from app.model_gateway.gateway import ModelGateway
from app.orchestrator.dependencies import get_execution_planner, get_model_gateway
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.router import (
    GenerationRequest,
    generate_knowledge_graph,
    get_knowledge_graph,
)

router = APIRouter(tags=["Secure knowledge graph"])


@router.post(
    "/documents/{document_id}/knowledge-graph/generate",
    response_model=ApiSuccessResponse[KnowledgeGraphGenerationResult],
    status_code=status.HTTP_201_CREATED,
)
def generate_owned_knowledge_graph(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_ASK_AI))],
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    planner: Annotated[ExecutionPlanner, Depends(get_execution_planner)],
    body: GenerationRequest | None = None,
) -> ApiSuccessResponse[KnowledgeGraphGenerationResult]:
    get_visible_document(session, actor, document_id)
    return generate_knowledge_graph(
        document_id=document_id,
        session=session,
        gateway=gateway,
        planner=planner,
        body=body,
    )


@router.get(
    "/documents/{document_id}/knowledge-graph",
    response_model=ApiSuccessResponse[KnowledgeGraphView],
)
def get_owned_knowledge_graph(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[KnowledgeGraphView]:
    get_visible_document(session, actor, document_id)
    return get_knowledge_graph(document_id=document_id, session=session)

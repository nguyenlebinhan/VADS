from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.permissions import Permission
from app.dependencies.permissions import require_permission
from app.model.users import User
from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.database_rag_service import DatabaseRagService

router = APIRouter(prefix="/rag", tags=["Secure RAG"])


def get_database_rag_service(
    session: Annotated[Session, Depends(get_db)],
) -> DatabaseRagService:
    return DatabaseRagService(session)


@router.post("/query", response_model=RagQueryResponse)
def query_database_rag(
    payload: RagQueryRequest,
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_ASK_AI))],
    service: Annotated[DatabaseRagService, Depends(get_database_rag_service)],
) -> RagQueryResponse:
    return service.answer(actor=actor, payload=payload)

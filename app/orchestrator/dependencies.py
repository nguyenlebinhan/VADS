from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chunking.reader import SqlAlchemyDocumentChunkReader
from app.citations.validator import CitationValidator
from app.config.database import get_db
from app.model.documents import Document
from app.model_gateway.gateway import ModelGateway, UnavailableModelGateway
from app.model_gateway.registry import ModelRegistry, build_default_registry
from app.model_gateway.router import ModelRouter
from app.orchestrator.planner import ExecutionPlanner


@lru_cache
def get_model_registry() -> ModelRegistry:
    return build_default_registry()


def get_model_gateway(request: Request) -> ModelGateway:
    gateway = getattr(request.app.state, "model_gateway", None)
    return gateway if gateway is not None else UnavailableModelGateway()


def get_execution_planner(
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> ExecutionPlanner:
    return ExecutionPlanner(ModelRouter(registry))


def build_citation_validator(session: Session) -> CitationValidator:
    def document_exists(document_id: str) -> bool:
        statement = select(Document.id).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
        return session.scalar(statement) is not None

    return CitationValidator(
        SqlAlchemyDocumentChunkReader(session),
        document_exists=document_exists,
    )


def get_citation_validator(
    session: Annotated[Session, Depends(get_db)],
) -> CitationValidator:
    return build_citation_validator(session)

from __future__ import annotations

import logging

from app.chunking.reader import SqlAlchemyDocumentChunkReader
from app.config.celery_app import celery_app
from app.config.database import SessionLocal
from app.config.settings import get_settings
from app.model_gateway.fpt_ai import build_fpt_ai_gateway
from app.model_gateway.gateway import MetadataModelGateway
from app.model_gateway.registry import build_default_registry
from app.model_gateway.router import ModelRouter
from app.orchestrator.dependencies import build_citation_validator
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.repository import WorkflowRepository
from app.orchestrator.schemas import ExecutionPlan, WorkflowStatus
from app.orchestrator.service import DocumentAnalysisOrchestrator
from app.utils.model_registry import import_models

logger = logging.getLogger(__name__)
import_models()


@celery_app.task(name="vads.analysis.run_document")
def analyze_document_workflow(workflow_id: str) -> None:
    with SessionLocal() as session:
        repository = WorkflowRepository(session)
        workflow = repository.get(workflow_id)
        if workflow is None or workflow.status != WorkflowStatus.PLANNED.value:
            return
        plan = ExecutionPlan.model_validate(workflow.plan)
        planner = ExecutionPlanner(ModelRouter(build_default_registry()))
        gateway = MetadataModelGateway(
            build_fpt_ai_gateway(get_settings()),
            {"private": plan.private_processing},
        )
        try:
            DocumentAnalysisOrchestrator(
                session,
                gateway=gateway,
                planner=planner,
                chunk_reader=SqlAlchemyDocumentChunkReader(session),
                citation_validator=build_citation_validator(session),
            ).analyze(
                plan.document_id or "",
                private=plan.private_processing,
                plan=plan,
            )
        except Exception as exc:
            session.rollback()
            logger.exception(
                "Document analysis workflow failed",
                extra={"workflow_id": workflow_id},
            )
            repository = WorkflowRepository(session)
            if repository.get(workflow_id) is not None:
                repository.complete(
                    workflow_id,
                    status=WorkflowStatus.FAILED,
                    result={
                        "workflowId": workflow_id,
                        "status": WorkflowStatus.FAILED.value,
                        "steps": [],
                    },
                    error_message=f"{type(exc).__name__}: {exc}",
                )
                session.commit()

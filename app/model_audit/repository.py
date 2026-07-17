from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model_audit.models import ModelExecution


class ModelExecutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, execution: ModelExecution) -> ModelExecution:
        self.session.add(execution)
        self.session.flush()
        return execution

    def list_for_workflow(self, workflow_id: str) -> list[ModelExecution]:
        statement = (
            select(ModelExecution)
            .where(ModelExecution.workflow_id == workflow_id)
            .order_by(ModelExecution.started_at, ModelExecution.attempt_number)
        )
        return list(self.session.scalars(statement))

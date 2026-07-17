from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model_audit.repository import ModelExecutionRepository
from app.orchestrator.models import AIWorkflow, AIWorkflowStep
from app.orchestrator.schemas import (
    ExecutionPlan,
    ModelExecutionView,
    StepStatus,
    WorkflowStatus,
    WorkflowStepView,
    WorkflowView,
)


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, plan: ExecutionPlan) -> AIWorkflow:
        workflow = AIWorkflow(
            id=plan.workflow_id,
            document_id=plan.document_id,
            intent=plan.intent.value,
            status=WorkflowStatus.PLANNED.value,
            private_processing=plan.private_processing,
            plan=plan.model_dump(mode="json", by_alias=True),
        )
        self.session.add(workflow)
        self.session.flush()
        for step in plan.steps:
            self.session.add(
                AIWorkflowStep(
                    workflow_id=workflow.id,
                    step_id=step.step_id,
                    task_type=step.task_type.value,
                    executor=step.executor,
                    reason_for_selection=step.reason_for_selection,
                    depends_on=step.depends_on,
                    can_run_in_parallel=step.can_run_in_parallel,
                    timeout_seconds=step.timeout_seconds,
                    max_retries=step.max_retries,
                    fallback_model=step.fallback_model,
                    expected_output_schema=step.expected_output_schema,
                    status=StepStatus.PENDING.value,
                )
            )
        self.session.flush()
        return workflow

    def get(self, workflow_id: str) -> AIWorkflow | None:
        return self.session.get(AIWorkflow, workflow_id)

    def get_step(self, workflow_id: str, step_id: str) -> AIWorkflowStep:
        statement = select(AIWorkflowStep).where(
            AIWorkflowStep.workflow_id == workflow_id,
            AIWorkflowStep.step_id == step_id,
        )
        step = self.session.scalar(statement)
        if step is None:
            raise LookupError(f"Workflow step not found: {workflow_id}/{step_id}")
        return step

    def list_steps(self, workflow_id: str) -> list[AIWorkflowStep]:
        statement = (
            select(AIWorkflowStep)
            .where(AIWorkflowStep.workflow_id == workflow_id)
            .order_by(AIWorkflowStep.created_at, AIWorkflowStep.step_id)
        )
        return list(self.session.scalars(statement))

    def mark_running(self, workflow_id: str) -> None:
        workflow = self._required(workflow_id)
        workflow.status = WorkflowStatus.RUNNING.value
        workflow.started_at = datetime.now(UTC)
        self.session.flush()

    def update_step(
        self,
        workflow_id: str,
        step_id: str,
        *,
        status: StepStatus,
        output: dict[str, Any] | list[Any] | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> AIWorkflowStep:
        step = self.get_step(workflow_id, step_id)
        step.status = status.value
        step.output = output
        step.error_message = error_message
        if started_at is not None:
            step.started_at = started_at
        if completed_at is not None:
            step.completed_at = completed_at
        self.session.flush()
        return step

    def complete(
        self,
        workflow_id: str,
        *,
        status: WorkflowStatus,
        result: dict[str, Any],
        error_message: str | None = None,
    ) -> AIWorkflow:
        workflow = self._required(workflow_id)
        workflow.status = status.value
        workflow.result = result
        workflow.error_message = error_message
        workflow.completed_at = datetime.now(UTC)
        self.session.flush()
        return workflow

    def view(self, workflow_id: str) -> WorkflowView | None:
        workflow = self.get(workflow_id)
        if workflow is None:
            return None
        steps = [
            WorkflowStepView.model_validate(
                {
                    "id": step.id,
                    "step_id": step.step_id,
                    "task_type": step.task_type,
                    "executor": step.executor,
                    "reason_for_selection": step.reason_for_selection,
                    "depends_on": step.depends_on,
                    "can_run_in_parallel": step.can_run_in_parallel,
                    "timeout_seconds": step.timeout_seconds,
                    "max_retries": step.max_retries,
                    "fallback_model": step.fallback_model,
                    "expected_output_schema": step.expected_output_schema,
                    "status": step.status,
                    "output": step.output,
                    "error_message": step.error_message,
                }
            )
            for step in self.list_steps(workflow_id)
        ]
        executions = [
            ModelExecutionView.model_validate(execution)
            for execution in ModelExecutionRepository(self.session).list_for_workflow(workflow_id)
        ]
        return WorkflowView(
            workflowId=workflow.id,
            documentId=workflow.document_id,
            intent=workflow.intent,
            status=workflow.status,
            privateProcessing=workflow.private_processing,
            plan=workflow.plan,
            result=workflow.result,
            errorMessage=workflow.error_message,
            createdAt=workflow.created_at,
            updatedAt=workflow.updated_at,
            startedAt=workflow.started_at,
            completedAt=workflow.completed_at,
            steps=steps,
            modelExecutions=executions,
        )

    def _required(self, workflow_id: str) -> AIWorkflow:
        workflow = self.get(workflow_id)
        if workflow is None:
            raise LookupError(f"Workflow not found: {workflow_id}")
        return workflow

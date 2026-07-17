from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import Field, model_validator

from app.common.contracts import APIModel
from app.model_gateway.schemas import TaskType


class WorkflowIntent(str, Enum):
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"
    KNOWLEDGE_GRAPH_GENERATION = "KNOWLEDGE_GRAPH_GENERATION"
    CRITICAL_QUESTION_GENERATION = "CRITICAL_QUESTION_GENERATION"
    CROSS_DOCUMENT_ANALYSIS = "CROSS_DOCUMENT_ANALYSIS"


class WorkflowStatus(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionStep(APIModel):
    step_id: str = Field(min_length=1, max_length=100)
    task_type: TaskType
    executor: str = Field(min_length=1, max_length=100)
    reason_for_selection: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    can_run_in_parallel: bool = False
    timeout_seconds: int = Field(default=90, ge=1, le=900)
    max_retries: int = Field(default=2, ge=0, le=2)
    fallback_model: str | None = None
    expected_output_schema: str = Field(min_length=1, max_length=255)


class ExecutionPlan(APIModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    intent: WorkflowIntent
    document_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    private_processing: bool = False
    steps: list[ExecutionStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dag(self) -> ExecutionPlan:
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("stepId values must be unique")
        known = set(step_ids)
        graph = {step.step_id: step.depends_on for step in self.steps}
        for step_id, dependencies in graph.items():
            unknown = set(dependencies) - known
            if unknown:
                raise ValueError(f"Step {step_id} has unknown dependencies: {sorted(unknown)}")
            if step_id in dependencies:
                raise ValueError(f"Step {step_id} cannot depend on itself")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ValueError("Workflow dependencies contain a cycle")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in graph[step_id]:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in step_ids:
            visit(step_id)
        if self.document_id and self.document_ids and self.document_id not in self.document_ids:
            raise ValueError("documentId must be included in documentIds when both are supplied")
        return self


class StepExecutionResult(APIModel):
    step_id: str
    task_type: TaskType
    executor: str
    status: StepStatus
    attempts: int
    used_fallback: bool = False
    output: Any | None = None
    error: str | None = None


class WorkflowExecutionResult(APIModel):
    workflow_id: str
    status: WorkflowStatus
    steps: list[StepExecutionResult]


class ModelExecutionView(APIModel):
    id: str
    model_alias: str
    task_type: str
    attempt_number: int
    is_fallback: bool
    status: str
    latency_ms: int
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime


class WorkflowStepView(APIModel):
    id: str
    step_id: str
    task_type: str
    executor: str
    reason_for_selection: str
    depends_on: list[str]
    can_run_in_parallel: bool
    timeout_seconds: int
    max_retries: int
    fallback_model: str | None = None
    expected_output_schema: str
    status: str
    output: Any | None = None
    error_message: str | None = None


class WorkflowView(APIModel):
    workflow_id: str
    document_id: str | None = None
    intent: str
    status: str
    private_processing: bool
    plan: dict[str, Any]
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    steps: list[WorkflowStepView] = Field(default_factory=list)
    model_executions: list[ModelExecutionView] = Field(default_factory=list)

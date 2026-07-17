from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.model_audit.models import ModelExecution
from app.model_audit.repository import ModelExecutionRepository
from app.model_gateway.schemas import TaskType
from app.orchestrator.repository import WorkflowRepository
from app.orchestrator.schemas import (
    ExecutionPlan,
    ExecutionStep,
    StepExecutionResult,
    StepStatus,
    WorkflowExecutionResult,
    WorkflowStatus,
)

StepHandler = Callable[[ExecutionStep, str, Mapping[str, Any]], Any]

MANUAL_REVIEW_TASKS = {
    TaskType.DIFFICULT_PAGE_ANALYSIS,
    TaskType.LAYOUT_TABLE_ANALYSIS,
    TaskType.OCR_IMAGE_REVIEW,
}


class StepNeedsReview(RuntimeError):
    pass


@dataclass(frozen=True)
class AttemptTrace:
    model_alias: str
    attempt_number: int
    is_fallback: bool
    started_at: datetime
    completed_at: datetime
    latency_ms: int
    status: str
    output: dict[str, Any] | list[Any] | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class _StepOutcome:
    result: StepExecutionResult
    traces: list[AttemptTrace]
    started_at: datetime
    completed_at: datetime


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"value": str(value)}


class WorkflowExecutor:
    """Executes a validated DAG, with bounded retry/fallback and persistent audit."""

    def __init__(self, session: Session, *, max_parallel_workers: int = 4) -> None:
        self.session = session
        self.workflow_repository = WorkflowRepository(session)
        self.audit_repository = ModelExecutionRepository(session)
        self.max_parallel_workers = max(1, max_parallel_workers)

    def execute(
        self,
        plan: ExecutionPlan,
        handlers: Mapping[TaskType, StepHandler],
        *,
        persist_plan: bool = True,
    ) -> WorkflowExecutionResult:
        if persist_plan:
            self.workflow_repository.create(plan)
        elif self.workflow_repository.get(plan.workflow_id) is None:
            raise LookupError(f"Workflow plan was not persisted: {plan.workflow_id}")
        self.workflow_repository.mark_running(plan.workflow_id)
        self.session.commit()

        pending = {step.step_id: step for step in plan.steps}
        results: dict[str, StepExecutionResult] = {}
        outputs: dict[str, Any] = {}

        while pending:
            blocked = [
                step
                for step in pending.values()
                if any(
                    dependency in results
                    and results[dependency].status
                    in {StepStatus.FAILED, StepStatus.SKIPPED, StepStatus.NEEDS_REVIEW}
                    for dependency in step.depends_on
                )
            ]
            for step in blocked:
                result = StepExecutionResult(
                    stepId=step.step_id,
                    taskType=step.task_type,
                    executor=step.executor,
                    status=StepStatus.SKIPPED,
                    attempts=0,
                    error="Dependency did not complete successfully",
                )
                results[step.step_id] = result
                self.workflow_repository.update_step(
                    plan.workflow_id,
                    step.step_id,
                    status=StepStatus.SKIPPED,
                    error_message=result.error,
                    completed_at=datetime.now(UTC),
                )
                pending.pop(step.step_id)
            if blocked:
                self.session.commit()
                continue

            ready = [
                step
                for step in pending.values()
                if all(dependency in results for dependency in step.depends_on)
            ]
            if not ready:
                raise RuntimeError("Workflow DAG made no progress")
            parallel = [step for step in ready if step.can_run_in_parallel]
            batch = parallel if parallel else [ready[0]]
            batch_outcomes = self._run_batch(batch, handlers, outputs)
            for step, outcome in batch_outcomes:
                results[step.step_id] = outcome.result
                if outcome.result.status == StepStatus.COMPLETED:
                    outputs[step.step_id] = outcome.result.output
                self._persist_outcome(plan.workflow_id, step, outcome)
                pending.pop(step.step_id)
            self.session.commit()

        ordered = [results[step.step_id] for step in plan.steps]
        if any(result.status == StepStatus.FAILED for result in ordered):
            status = WorkflowStatus.FAILED
        elif any(
            result.status in {StepStatus.NEEDS_REVIEW, StepStatus.SKIPPED} for result in ordered
        ):
            status = WorkflowStatus.NEEDS_REVIEW
        else:
            status = WorkflowStatus.COMPLETED
        workflow_result = WorkflowExecutionResult(
            workflowId=plan.workflow_id,
            status=status,
            steps=ordered,
        )
        errors = [result.error for result in ordered if result.error]
        self.workflow_repository.complete(
            plan.workflow_id,
            status=status,
            result=workflow_result.model_dump(mode="json", by_alias=True),
            error_message="; ".join(errors) if errors else None,
        )
        self.session.commit()
        return workflow_result

    def _run_batch(
        self,
        steps: list[ExecutionStep],
        handlers: Mapping[TaskType, StepHandler],
        outputs: Mapping[str, Any],
    ) -> list[tuple[ExecutionStep, _StepOutcome]]:
        if len(steps) == 1:
            step = steps[0]
            return [(step, self._run_step(step, handlers, outputs))]
        completed: dict[str, _StepOutcome] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_parallel_workers, len(steps))) as pool:
            futures = {
                pool.submit(self._run_step, step, handlers, dict(outputs)): step for step in steps
            }
            for future in as_completed(futures):
                step = futures[future]
                completed[step.step_id] = future.result()
        return [(step, completed[step.step_id]) for step in steps]

    @staticmethod
    def _run_step(
        step: ExecutionStep,
        handlers: Mapping[TaskType, StepHandler],
        outputs: Mapping[str, Any],
    ) -> _StepOutcome:
        started_at = datetime.now(UTC)
        handler = handlers.get(step.task_type)
        if handler is None:
            error = f"No handler registered for {step.task_type.value}"
            result = StepExecutionResult(
                stepId=step.step_id,
                taskType=step.task_type,
                executor=step.executor,
                status=StepStatus.FAILED,
                attempts=0,
                error=error,
            )
            return _StepOutcome(result, [], started_at, datetime.now(UTC))

        dependencies = {key: outputs[key] for key in step.depends_on}
        traces: list[AttemptTrace] = []
        candidates = [(step.executor, False, step.max_retries + 1)]
        if step.fallback_model:
            candidates.append((step.fallback_model, True, 1))
        last_error: Exception | None = None
        attempt_number = 0

        for model_alias, is_fallback, attempt_count in candidates:
            for _ in range(attempt_count):
                attempt_number += 1
                attempt_started = datetime.now(UTC)
                monotonic_start = time.monotonic()
                try:
                    output = handler(step, model_alias, dependencies)
                    json_output = _json_value(output)
                    attempt_completed = datetime.now(UTC)
                    traces.append(
                        AttemptTrace(
                            model_alias=model_alias,
                            attempt_number=attempt_number,
                            is_fallback=is_fallback,
                            started_at=attempt_started,
                            completed_at=attempt_completed,
                            latency_ms=int((time.monotonic() - monotonic_start) * 1000),
                            status=StepStatus.COMPLETED.value,
                            output=json_output,
                        )
                    )
                    result = StepExecutionResult(
                        stepId=step.step_id,
                        taskType=step.task_type,
                        executor=model_alias,
                        status=StepStatus.COMPLETED,
                        attempts=attempt_number,
                        usedFallback=is_fallback,
                        output=json_output,
                    )
                    return _StepOutcome(result, traces, started_at, attempt_completed)
                except StepNeedsReview as exc:
                    attempt_completed = datetime.now(UTC)
                    traces.append(
                        AttemptTrace(
                            model_alias=model_alias,
                            attempt_number=attempt_number,
                            is_fallback=is_fallback,
                            started_at=attempt_started,
                            completed_at=attempt_completed,
                            latency_ms=int((time.monotonic() - monotonic_start) * 1000),
                            status=StepStatus.NEEDS_REVIEW.value,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )
                    result = StepExecutionResult(
                        stepId=step.step_id,
                        taskType=step.task_type,
                        executor=model_alias,
                        status=StepStatus.NEEDS_REVIEW,
                        attempts=attempt_number,
                        usedFallback=is_fallback,
                        error=str(exc),
                    )
                    return _StepOutcome(result, traces, started_at, attempt_completed)
                except Exception as exc:  # adapters expose provider-specific exception types
                    last_error = exc
                    attempt_completed = datetime.now(UTC)
                    traces.append(
                        AttemptTrace(
                            model_alias=model_alias,
                            attempt_number=attempt_number,
                            is_fallback=is_fallback,
                            started_at=attempt_started,
                            completed_at=attempt_completed,
                            latency_ms=int((time.monotonic() - monotonic_start) * 1000),
                            status=StepStatus.FAILED.value,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )

        completed_at = datetime.now(UTC)
        exhausted_status = (
            StepStatus.NEEDS_REVIEW if step.task_type in MANUAL_REVIEW_TASKS else StepStatus.FAILED
        )
        result = StepExecutionResult(
            stepId=step.step_id,
            taskType=step.task_type,
            executor=traces[-1].model_alias if traces else step.executor,
            status=exhausted_status,
            attempts=attempt_number,
            usedFallback=bool(traces and traces[-1].is_fallback),
            error=str(last_error) if last_error else "Step failed",
        )
        return _StepOutcome(result, traces, started_at, completed_at)

    def _persist_outcome(
        self,
        workflow_id: str,
        step: ExecutionStep,
        outcome: _StepOutcome,
    ) -> None:
        db_step = self.workflow_repository.update_step(
            workflow_id,
            step.step_id,
            status=outcome.result.status,
            output=outcome.result.output,
            error_message=outcome.result.error,
            started_at=outcome.started_at,
            completed_at=outcome.completed_at,
        )
        if step.executor == "RULE_ENGINE":
            return
        for trace in outcome.traces:
            self.audit_repository.add(
                ModelExecution(
                    workflow_id=workflow_id,
                    workflow_step_id=db_step.id,
                    model_alias=trace.model_alias,
                    task_type=step.task_type.value,
                    attempt_number=trace.attempt_number,
                    is_fallback=trace.is_fallback,
                    status=trace.status,
                    request_metadata={
                        "expectedOutputSchema": step.expected_output_schema,
                        "timeoutSeconds": step.timeout_seconds,
                    },
                    response_metadata={},
                    output_snapshot=trace.output,
                    error_type=trace.error_type,
                    error_message=trace.error_message,
                    latency_ms=trace.latency_ms,
                    started_at=trace.started_at,
                    completed_at=trace.completed_at,
                )
            )

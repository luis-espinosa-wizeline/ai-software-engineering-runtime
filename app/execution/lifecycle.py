"""Immutable lifecycle operations for the workflow execution aggregate."""

from collections.abc import Callable
from datetime import datetime

from app.execution.errors import (
    InvalidLifecycleTimestamp,
    InvalidStepTransition,
    InvalidWorkflowTransition,
    UnknownWorkflowStep,
)
from app.execution.models import (
    ExecutionStepStatus,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStepExecution,
)
from app.shared import Metadata, WorkflowStepId
from app.workflows import WorkflowResult

type StepTransition = Callable[[WorkflowStepExecution], WorkflowStepExecution]


def start_execution(
    execution: WorkflowExecution,
    *,
    started_at: datetime,
) -> WorkflowExecution:
    """Start a pending workflow execution."""
    _require_workflow_status(execution, WorkflowStatus.PENDING, "start")
    _require_timestamp_at_or_after(started_at, execution.created_at, "created_at")
    return execution.model_copy(
        update={
            "status": WorkflowStatus.RUNNING,
            "started_at": started_at,
        }
    )


def complete_execution(
    execution: WorkflowExecution,
    *,
    result: WorkflowResult | None = None,
    completed_at: datetime,
) -> WorkflowExecution:
    """Complete a running workflow execution successfully."""
    _require_workflow_status(execution, WorkflowStatus.RUNNING, "complete")
    if result is None:
        raise InvalidWorkflowTransition("Successful execution requires a workflow result")
    started_at = _required_started_at(execution)
    _require_timestamp_at_or_after(completed_at, started_at, "started_at")

    incomplete_steps = tuple(
        step.step_id
        for step in execution.steps
        if step.status in {ExecutionStepStatus.PENDING, ExecutionStepStatus.RUNNING}
    )
    if incomplete_steps:
        identifiers = ", ".join(incomplete_steps)
        raise InvalidWorkflowTransition(
            f"Cannot complete execution with incomplete steps: {identifiers}"
        )

    failed_steps = tuple(
        step.step_id for step in execution.steps if step.status is ExecutionStepStatus.FAILED
    )
    if failed_steps:
        identifiers = ", ".join(failed_steps)
        raise InvalidWorkflowTransition(
            f"Cannot complete execution with failed steps: {identifiers}"
        )

    return execution.model_copy(
        update={
            "status": WorkflowStatus.SUCCEEDED,
            "completed_at": completed_at,
            "result": result,
        }
    )


def fail_execution(
    execution: WorkflowExecution,
    *,
    reason: str,
    completed_at: datetime,
) -> WorkflowExecution:
    """Fail a running workflow execution."""
    _require_workflow_status(execution, WorkflowStatus.RUNNING, "fail")
    started_at = _required_started_at(execution)
    _require_timestamp_at_or_after(completed_at, started_at, "started_at")
    return execution.model_copy(
        update={
            "status": WorkflowStatus.FAILED,
            "completed_at": completed_at,
            "error": reason,
        }
    )


def cancel_execution(
    execution: WorkflowExecution,
    *,
    completed_at: datetime,
    reason: str | None = None,
) -> WorkflowExecution:
    """Cancel a pending or running workflow execution."""
    if execution.status not in {WorkflowStatus.PENDING, WorkflowStatus.RUNNING}:
        raise InvalidWorkflowTransition(
            f"Cannot cancel execution in {execution.status.value} status"
        )

    baseline = (
        _required_started_at(execution)
        if execution.status is WorkflowStatus.RUNNING
        else execution.created_at
    )
    baseline_name = "started_at" if execution.status is WorkflowStatus.RUNNING else "created_at"
    _require_timestamp_at_or_after(completed_at, baseline, baseline_name)
    return execution.model_copy(
        update={
            "status": WorkflowStatus.CANCELLED,
            "completed_at": completed_at,
            "error": reason,
        }
    )


def start_step(
    execution: WorkflowExecution,
    step_id: WorkflowStepId,
    *,
    started_at: datetime,
) -> WorkflowExecution:
    """Start a pending step through the workflow execution aggregate."""
    execution_started_at = _require_running_execution(execution)

    def transition(step: WorkflowStepExecution) -> WorkflowStepExecution:
        _require_step_status(step, ExecutionStepStatus.PENDING, "start")
        _require_timestamp_at_or_after(started_at, execution_started_at, "execution started_at")
        return step.model_copy(
            update={
                "status": ExecutionStepStatus.RUNNING,
                "started_at": started_at,
            }
        )

    return _update_step(execution, step_id, transition)


def complete_step(
    execution: WorkflowExecution,
    step_id: WorkflowStepId,
    *,
    completed_at: datetime,
) -> WorkflowExecution:
    """Complete a running step through the workflow execution aggregate."""
    _require_running_execution(execution)

    def transition(step: WorkflowStepExecution) -> WorkflowStepExecution:
        _require_step_status(step, ExecutionStepStatus.RUNNING, "complete")
        started_at = _required_step_started_at(step)
        _require_timestamp_at_or_after(completed_at, started_at, "step started_at")
        return step.model_copy(
            update={
                "status": ExecutionStepStatus.SUCCEEDED,
                "completed_at": completed_at,
            }
        )

    return _update_step(execution, step_id, transition)


def fail_step(
    execution: WorkflowExecution,
    step_id: WorkflowStepId,
    *,
    error: str,
    completed_at: datetime,
) -> WorkflowExecution:
    """Fail a running step through the workflow execution aggregate."""
    _require_running_execution(execution)

    def transition(step: WorkflowStepExecution) -> WorkflowStepExecution:
        _require_step_status(step, ExecutionStepStatus.RUNNING, "fail")
        started_at = _required_step_started_at(step)
        _require_timestamp_at_or_after(completed_at, started_at, "step started_at")
        return step.model_copy(
            update={
                "status": ExecutionStepStatus.FAILED,
                "completed_at": completed_at,
                "error": error,
            }
        )

    return _update_step(execution, step_id, transition)


def skip_step(
    execution: WorkflowExecution,
    step_id: WorkflowStepId,
    *,
    completed_at: datetime,
    reason: str | None = None,
) -> WorkflowExecution:
    """Skip a pending step through the workflow execution aggregate."""
    execution_started_at = _require_running_execution(execution)

    def transition(step: WorkflowStepExecution) -> WorkflowStepExecution:
        _require_step_status(step, ExecutionStepStatus.PENDING, "skip")
        _require_timestamp_at_or_after(
            completed_at,
            execution_started_at,
            "execution started_at",
        )
        details: Metadata = dict(step.details)
        if reason is not None:
            details["skip_reason"] = reason
        return step.model_copy(
            update={
                "status": ExecutionStepStatus.SKIPPED,
                "completed_at": completed_at,
                "details": details,
            }
        )

    return _update_step(execution, step_id, transition)


def _update_step(
    execution: WorkflowExecution,
    step_id: WorkflowStepId,
    transition: StepTransition,
) -> WorkflowExecution:
    matching_steps = tuple(step for step in execution.steps if step.step_id == step_id)
    if not matching_steps:
        raise UnknownWorkflowStep(f"Unknown workflow step: {step_id}")

    updated_steps = tuple(
        transition(step) if step.step_id == step_id else step for step in execution.steps
    )
    return execution.model_copy(update={"steps": updated_steps})


def _require_workflow_status(
    execution: WorkflowExecution,
    expected: WorkflowStatus,
    operation: str,
) -> None:
    if execution.status is not expected:
        raise InvalidWorkflowTransition(
            f"Cannot {operation} execution in {execution.status.value} status"
        )


def _require_step_status(
    step: WorkflowStepExecution,
    expected: ExecutionStepStatus,
    operation: str,
) -> None:
    if step.status is not expected:
        raise InvalidStepTransition(
            f"Cannot {operation} step {step.step_id} in {step.status.value} status"
        )


def _require_running_execution(execution: WorkflowExecution) -> datetime:
    _require_workflow_status(execution, WorkflowStatus.RUNNING, "change a step for")
    return _required_started_at(execution)


def _required_started_at(execution: WorkflowExecution) -> datetime:
    if execution.started_at is None:
        raise InvalidWorkflowTransition("Running execution has no start timestamp")
    return execution.started_at


def _required_step_started_at(step: WorkflowStepExecution) -> datetime:
    if step.started_at is None:
        raise InvalidStepTransition(f"Running step {step.step_id} has no start timestamp")
    return step.started_at


def _require_timestamp_at_or_after(
    timestamp: datetime,
    baseline: datetime,
    baseline_name: str,
) -> None:
    _require_aware_timestamp(timestamp)
    _require_aware_timestamp(baseline)
    if timestamp < baseline:
        raise InvalidLifecycleTimestamp(
            f"Lifecycle timestamp cannot be earlier than {baseline_name}"
        )


def _require_aware_timestamp(timestamp: datetime) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InvalidLifecycleTimestamp("Lifecycle timestamps must be timezone-aware")

from datetime import UTC, datetime, timedelta

import pytest

from app.execution import (
    ExecutionContext,
    ExecutionStepStatus,
    InvalidLifecycleTimestamp,
    InvalidStepTransition,
    InvalidWorkflowSteps,
    InvalidWorkflowTransition,
    UnknownWorkflowStep,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStepExecution,
    cancel_execution,
    complete_execution,
    complete_step,
    fail_execution,
    fail_step,
    skip_step,
    start_execution,
    start_step,
)
from app.workflows import (
    WorkflowDefinition,
    WorkflowRequest,
    WorkflowResult,
    WorkflowStepDefinition,
)

CREATED_AT = datetime(2026, 1, 1, 12, tzinfo=UTC)
STARTED_AT = CREATED_AT + timedelta(minutes=1)
COMPLETED_AT = STARTED_AT + timedelta(minutes=1)


def make_execution() -> WorkflowExecution:
    return WorkflowExecution(
        definition=WorkflowDefinition(
            workflow_id="code-review",
            name="Code review",
            version="1",
            steps=(
                WorkflowStepDefinition(step_id="collect-context", name="Collect context"),
                WorkflowStepDefinition(step_id="review", name="Review change"),
            ),
        ),
        request=WorkflowRequest(requested_at=CREATED_AT),
        context=ExecutionContext(),
        created_at=CREATED_AT,
    )


def running_execution() -> WorkflowExecution:
    return start_execution(make_execution(), started_at=STARTED_AT)


def execution_with_finished_steps() -> WorkflowExecution:
    execution = running_execution()
    execution = start_step(execution, "collect-context", started_at=STARTED_AT)
    execution = complete_step(execution, "collect-context", completed_at=COMPLETED_AT)
    return skip_step(execution, "review", completed_at=COMPLETED_AT, reason="Not required")


def test_creation_initializes_steps_in_definition_order() -> None:
    execution = make_execution()

    assert tuple(step.step_id for step in execution.steps) == ("collect-context", "review")
    assert all(step.status is ExecutionStepStatus.PENDING for step in execution.steps)


def test_creation_rejects_duplicate_or_mismatched_step_identifiers() -> None:
    duplicate_definition = WorkflowDefinition(
        workflow_id="duplicate",
        name="Duplicate",
        version="1",
        steps=(
            WorkflowStepDefinition(step_id="same", name="First"),
            WorkflowStepDefinition(step_id="same", name="Second"),
        ),
    )

    with pytest.raises(InvalidWorkflowSteps, match="duplicate"):
        WorkflowExecution(
            definition=duplicate_definition,
            request=WorkflowRequest(requested_at=CREATED_AT),
            context=ExecutionContext(),
            created_at=CREATED_AT,
        )

    definition = make_execution().definition
    with pytest.raises(InvalidWorkflowSteps, match="definition order"):
        WorkflowExecution(
            definition=definition,
            request=WorkflowRequest(requested_at=CREATED_AT),
            context=ExecutionContext(),
            created_at=CREATED_AT,
            steps=(
                WorkflowStepExecution(
                    step_id="review",
                    status=ExecutionStepStatus.PENDING,
                ),
                WorkflowStepExecution(
                    step_id="collect-context",
                    status=ExecutionStepStatus.PENDING,
                ),
            ),
        )


def test_execution_starts_immutably() -> None:
    pending = make_execution()

    running = start_execution(pending, started_at=STARTED_AT)

    assert running is not pending
    assert pending.status is WorkflowStatus.PENDING
    assert pending.started_at is None
    assert running.status is WorkflowStatus.RUNNING
    assert running.started_at == STARTED_AT
    assert running.created_at == pending.created_at


def test_execution_cannot_start_twice() -> None:
    execution = running_execution()

    with pytest.raises(InvalidWorkflowTransition, match="running"):
        start_execution(execution, started_at=STARTED_AT)


def test_successful_completion_requires_running_execution_and_result() -> None:
    with pytest.raises(InvalidWorkflowTransition, match="pending"):
        complete_execution(
            make_execution(),
            result=WorkflowResult(summary="Done"),
            completed_at=COMPLETED_AT,
        )

    with pytest.raises(InvalidWorkflowTransition, match="requires a workflow result"):
        complete_execution(running_execution(), completed_at=COMPLETED_AT)


def test_successful_completion_rejects_incomplete_and_failed_steps() -> None:
    execution = running_execution()
    execution = start_step(execution, "collect-context", started_at=STARTED_AT)
    with pytest.raises(InvalidWorkflowTransition, match="incomplete steps"):
        complete_execution(
            execution,
            result=WorkflowResult(summary="Done"),
            completed_at=COMPLETED_AT,
        )

    execution = fail_step(
        execution,
        "collect-context",
        error="Context unavailable",
        completed_at=COMPLETED_AT,
    )
    execution = skip_step(execution, "review", completed_at=COMPLETED_AT)
    with pytest.raises(InvalidWorkflowTransition, match="failed steps"):
        complete_execution(
            execution,
            result=WorkflowResult(summary="Done"),
            completed_at=COMPLETED_AT,
        )


def test_execution_completes_successfully_and_immutably() -> None:
    running = execution_with_finished_steps()
    result = WorkflowResult(summary="Review complete")

    succeeded = complete_execution(running, result=result, completed_at=COMPLETED_AT)

    assert succeeded is not running
    assert running.status is WorkflowStatus.RUNNING
    assert running.result is None
    assert succeeded.status is WorkflowStatus.SUCCEEDED
    assert succeeded.completed_at == COMPLETED_AT
    assert succeeded.result == result


def test_execution_fails_successfully() -> None:
    running = running_execution()

    failed = fail_execution(
        running,
        reason="Workflow could not continue",
        completed_at=COMPLETED_AT,
    )

    assert failed is not running
    assert running.status is WorkflowStatus.RUNNING
    assert running.error is None
    assert failed.status is WorkflowStatus.FAILED
    assert failed.completed_at == COMPLETED_AT
    assert failed.error == "Workflow could not continue"


def test_execution_cancels_from_pending_and_running() -> None:
    pending = make_execution()
    cancelled_pending = cancel_execution(
        pending,
        completed_at=STARTED_AT,
        reason="No longer needed",
    )
    running = running_execution()
    cancelled_running = cancel_execution(running, completed_at=COMPLETED_AT)

    assert pending.status is WorkflowStatus.PENDING
    assert cancelled_pending.status is WorkflowStatus.CANCELLED
    assert cancelled_pending.error == "No longer needed"
    assert running.status is WorkflowStatus.RUNNING
    assert cancelled_running.status is WorkflowStatus.CANCELLED
    assert cancelled_running.error is None


@pytest.mark.parametrize(
    "terminal_execution",
    [
        complete_execution(
            execution_with_finished_steps(),
            result=WorkflowResult(summary="Done"),
            completed_at=COMPLETED_AT,
        ),
        fail_execution(
            running_execution(),
            reason="Failed",
            completed_at=COMPLETED_AT,
        ),
        cancel_execution(make_execution(), completed_at=COMPLETED_AT),
    ],
)
def test_terminal_executions_reject_further_transitions(
    terminal_execution: WorkflowExecution,
) -> None:
    with pytest.raises(InvalidWorkflowTransition):
        start_execution(terminal_execution, started_at=COMPLETED_AT)
    with pytest.raises(InvalidWorkflowTransition):
        cancel_execution(terminal_execution, completed_at=COMPLETED_AT)


def test_execution_rejects_invalid_and_naive_timestamps() -> None:
    with pytest.raises(InvalidLifecycleTimestamp, match="created_at"):
        start_execution(make_execution(), started_at=CREATED_AT - timedelta(seconds=1))

    with pytest.raises(InvalidLifecycleTimestamp, match="timezone-aware"):
        start_execution(make_execution(), started_at=datetime(2026, 1, 1, 12))

    with pytest.raises(InvalidLifecycleTimestamp, match="started_at"):
        fail_execution(
            running_execution(),
            reason="Failed",
            completed_at=STARTED_AT - timedelta(seconds=1),
        )

    with pytest.raises(InvalidLifecycleTimestamp, match="timezone-aware"):
        cancel_execution(
            running_execution(),
            completed_at=datetime(2026, 1, 1, 12),
        )


def test_step_starts_and_completes_immutably() -> None:
    execution = running_execution()

    started = start_step(execution, "collect-context", started_at=STARTED_AT)
    completed = complete_step(started, "collect-context", completed_at=COMPLETED_AT)

    assert started is not execution
    assert execution.steps[0].status is ExecutionStepStatus.PENDING
    assert started.steps[0].status is ExecutionStepStatus.RUNNING
    assert started.steps[0].started_at == STARTED_AT
    assert completed is not started
    assert started.steps[0].completed_at is None
    assert completed.steps[0].status is ExecutionStepStatus.SUCCEEDED
    assert completed.steps[0].completed_at == COMPLETED_AT


def test_completing_step_preserves_details() -> None:
    pending = make_execution()
    execution = WorkflowExecution(
        definition=pending.definition,
        request=pending.request,
        context=pending.context,
        created_at=pending.created_at,
        steps=(
            WorkflowStepExecution(
                step_id="collect-context",
                status=ExecutionStepStatus.PENDING,
                details={"attempt": 1},
            ),
            WorkflowStepExecution(
                step_id="review",
                status=ExecutionStepStatus.PENDING,
            ),
        ),
    )
    execution = start_execution(execution, started_at=STARTED_AT)
    execution = start_step(execution, "collect-context", started_at=STARTED_AT)

    completed = complete_step(execution, "collect-context", completed_at=COMPLETED_AT)

    assert completed.steps[0].details == {"attempt": 1}


def test_step_fails_with_error() -> None:
    execution = start_step(
        running_execution(),
        "collect-context",
        started_at=STARTED_AT,
    )

    failed = fail_step(
        execution,
        "collect-context",
        error="Repository unavailable",
        completed_at=COMPLETED_AT,
    )

    assert execution.steps[0].status is ExecutionStepStatus.RUNNING
    assert failed.steps[0].status is ExecutionStepStatus.FAILED
    assert failed.steps[0].error == "Repository unavailable"
    assert failed.steps[0].completed_at == COMPLETED_AT


def test_pending_step_can_be_skipped_with_reason() -> None:
    execution = running_execution()

    skipped = skip_step(
        execution,
        "collect-context",
        completed_at=COMPLETED_AT,
        reason="Context already supplied",
    )

    assert execution.steps[0].status is ExecutionStepStatus.PENDING
    assert skipped.steps[0].status is ExecutionStepStatus.SKIPPED
    assert skipped.steps[0].completed_at == COMPLETED_AT
    assert skipped.steps[0].details["skip_reason"] == "Context already supplied"


def test_invalid_step_transitions_are_rejected() -> None:
    execution = start_step(
        running_execution(),
        "collect-context",
        started_at=STARTED_AT,
    )

    with pytest.raises(InvalidStepTransition, match="running"):
        start_step(execution, "collect-context", started_at=STARTED_AT)
    with pytest.raises(InvalidStepTransition, match="running"):
        skip_step(execution, "collect-context", completed_at=COMPLETED_AT)


def test_unknown_step_identifier_is_rejected() -> None:
    with pytest.raises(UnknownWorkflowStep, match="unknown"):
        start_step(running_execution(), "unknown", started_at=STARTED_AT)


def test_updating_one_step_preserves_order_and_other_steps() -> None:
    execution = running_execution()

    updated = start_step(execution, "review", started_at=STARTED_AT)

    assert tuple(step.step_id for step in updated.steps) == ("collect-context", "review")
    assert updated.steps[0] is execution.steps[0]
    assert updated.steps[0].status is ExecutionStepStatus.PENDING
    assert updated.steps[1].status is ExecutionStepStatus.RUNNING


def test_step_transitions_reject_invalid_and_naive_timestamps() -> None:
    execution = running_execution()
    with pytest.raises(InvalidLifecycleTimestamp, match="execution started_at"):
        start_step(
            execution,
            "collect-context",
            started_at=STARTED_AT - timedelta(seconds=1),
        )
    with pytest.raises(InvalidLifecycleTimestamp, match="timezone-aware"):
        start_step(
            execution,
            "collect-context",
            started_at=datetime(2026, 1, 1, 12),
        )

    started = start_step(execution, "collect-context", started_at=STARTED_AT)
    with pytest.raises(InvalidLifecycleTimestamp, match="step started_at"):
        complete_step(
            started,
            "collect-context",
            completed_at=STARTED_AT - timedelta(seconds=1),
        )

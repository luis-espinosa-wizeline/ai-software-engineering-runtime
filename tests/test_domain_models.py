from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.execution import (
    ExecutionContext,
    ExecutionStepStatus,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStepExecution,
)
from app.runtime import Trigger
from app.workflows import WorkflowDefinition, WorkflowRequest, WorkflowStepDefinition


def test_workflow_execution_exposes_the_runtime_aggregate() -> None:
    now = datetime.now(UTC)
    execution_id = UUID("00000000-0000-0000-0000-000000000001")
    execution = WorkflowExecution(
        definition=WorkflowDefinition(
            workflow_id="code-review",
            name="Code review",
            version="1",
            steps=(
                WorkflowStepDefinition(
                    step_id="review",
                    name="Review change",
                    required_capabilities=("review-code",),
                ),
            ),
            required_capabilities=("review-code",),
        ),
        request=WorkflowRequest(requested_at=now, correlation_id="change-42"),
        context=ExecutionContext(
            execution_id=execution_id,
            plan_id="code-review.1",
            inputs={"repository": "example/runtime"},
        ),
        execution_id=execution_id,
        created_at=now,
        steps=(
            WorkflowStepExecution(
                step_id="review",
                status=ExecutionStepStatus.PENDING,
            ),
        ),
    )

    assert execution.status is WorkflowStatus.PENDING
    assert execution.context.plan_id == "code-review.1"
    assert execution.context.inputs == {"repository": "example/runtime"}
    assert execution.definition.required_capabilities == ("review-code",)
    assert execution.definition.steps[0].name == "Review change"
    assert execution.steps[0].step_id == execution.definition.steps[0].step_id


def test_execution_context_stores_execution_inputs() -> None:
    context = ExecutionContext(
        execution_id=UUID("00000000-0000-0000-0000-000000000001"),
        plan_id="code-review.1",
        inputs={"source": "scheduled"},
    )

    assert context.inputs == {"source": "scheduled"}


def test_domain_models_are_immutable_and_reject_unknown_fields() -> None:
    trigger = Trigger(name="manual", kind="manual")

    with pytest.raises(ValidationError):
        Trigger(name="manual", kind="manual", provider="github")  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        trigger.name = "changed"

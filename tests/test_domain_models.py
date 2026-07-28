from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.execution import (
    ExecutionContext,
    ExecutionStepStatus,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStepExecution,
)
from app.runtime import Trigger, TriggerEvent, TriggerMetadata
from app.workflows import WorkflowDefinition, WorkflowRequest, WorkflowStepDefinition


def test_workflow_execution_exposes_the_runtime_aggregate() -> None:
    now = datetime.now(UTC)
    event = TriggerEvent(
        trigger=Trigger(name="manual", kind="manual"),
        metadata=TriggerMetadata(source="test", event_type="requested"),
        occurred_at=now,
    )
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
            trigger_event=event,
            values={"repository": "example/runtime"},
        ),
        created_at=now,
        steps=(
            WorkflowStepExecution(
                step_id="review",
                status=ExecutionStepStatus.PENDING,
            ),
        ),
    )

    assert execution.status is WorkflowStatus.PENDING
    assert execution.context.trigger_event == event
    assert execution.context.values == {"repository": "example/runtime"}
    assert execution.definition.required_capabilities == ("review-code",)
    assert execution.definition.steps[0].name == "Review change"
    assert execution.steps[0].step_id == execution.definition.steps[0].step_id


def test_execution_context_does_not_require_a_trigger_event() -> None:
    context = ExecutionContext(values={"source": "scheduled"})

    assert context.trigger_event is None


def test_domain_models_are_immutable_and_reject_unknown_fields() -> None:
    trigger = Trigger(name="manual", kind="manual")

    with pytest.raises(ValidationError):
        Trigger(name="manual", kind="manual", provider="github")  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        trigger.name = "changed"

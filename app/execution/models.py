"""Workflow execution aggregate and supporting values."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, model_validator

from app.execution.context import ExecutionContext
from app.execution.errors import InvalidWorkflowSteps
from app.policy import PolicyDecision
from app.shared import DomainModel, Metadata, RuntimeId, WorkflowStepId
from app.workflows import WorkflowDefinition, WorkflowRequest, WorkflowResult


class WorkflowStatus(StrEnum):
    """Lifecycle state of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStepStatus(StrEnum):
    """Lifecycle state of an individual execution step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStepExecution(DomainModel):
    """The recorded progress of one defined workflow step."""

    step_id: WorkflowStepId
    status: ExecutionStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    details: Metadata = Field(default_factory=dict)
    error: str | None = None


class WorkflowExecution(DomainModel):
    """Aggregate root representing one complete workflow lifecycle."""

    definition: WorkflowDefinition
    request: WorkflowRequest
    context: ExecutionContext
    status: WorkflowStatus = WorkflowStatus.PENDING
    execution_id: RuntimeId = Field(default_factory=uuid4)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    steps: tuple[WorkflowStepExecution, ...] = ()
    policy_decisions: tuple[PolicyDecision, ...] = ()
    result: WorkflowResult | None = None
    error: str | None = None
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def initialize_and_validate_steps(self) -> WorkflowExecution:
        """Initialize ordered step executions and enforce definition consistency."""
        definition_step_ids = tuple(step.step_id for step in self.definition.steps)

        if len(definition_step_ids) != len(set(definition_step_ids)):
            raise InvalidWorkflowSteps("Workflow definition contains duplicate step identifiers")

        if not self.steps:
            initialized_steps = tuple(
                WorkflowStepExecution(step_id=step_id, status=ExecutionStepStatus.PENDING)
                for step_id in definition_step_ids
            )
            object.__setattr__(self, "steps", initialized_steps)
            return self

        execution_step_ids = tuple(step.step_id for step in self.steps)
        if len(execution_step_ids) != len(set(execution_step_ids)):
            raise InvalidWorkflowSteps("Workflow execution contains duplicate step identifiers")
        if execution_step_ids != definition_step_ids:
            raise InvalidWorkflowSteps(
                "Workflow execution steps must match workflow definition order"
            )
        if any(step.status is not ExecutionStepStatus.PENDING for step in self.steps):
            raise InvalidWorkflowSteps("Workflow execution steps must initially be pending")

        return self

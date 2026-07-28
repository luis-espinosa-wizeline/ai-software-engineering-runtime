"""Workflow definition, request, and result models."""

from datetime import datetime

from pydantic import Field

from app.shared import (
    CapabilityId,
    DomainModel,
    JsonValue,
    Metadata,
    WorkflowId,
    WorkflowStepId,
)


class WorkflowStepDefinition(DomainModel):
    """A logical unit of work in a workflow definition."""

    step_id: WorkflowStepId
    name: str
    description: str | None = None
    required_capabilities: tuple[CapabilityId, ...] = ()
    metadata: Metadata = Field(default_factory=dict)


class WorkflowDefinition(DomainModel):
    """The versioned description of a workflow the Runtime can execute."""

    workflow_id: WorkflowId
    name: str
    version: str
    description: str | None = None
    steps: tuple[WorkflowStepDefinition, ...] = ()
    required_capabilities: tuple[CapabilityId, ...] = ()
    metadata: Metadata = Field(default_factory=dict)


class WorkflowRequest(DomainModel):
    """Inputs supplied for one execution of a workflow."""

    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    requested_at: datetime
    requested_by: str | None = None
    correlation_id: str | None = None


class WorkflowResult(DomainModel):
    """The final, provider-neutral output of a workflow execution."""

    outputs: dict[str, JsonValue] = Field(default_factory=dict)
    summary: str | None = None
    artifacts: tuple[str, ...] = ()
    metadata: Metadata = Field(default_factory=dict)

"""Workflow definition, request, and result models."""

from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.shared import (
    CapabilityId,
    DomainModel,
    JsonValue,
    Metadata,
    WorkflowId,
    WorkflowStepId,
)

type WorkflowPlanningIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
type WorkflowInputSource = WorkflowInputReference | WorkflowStepOutputReference


class WorkflowInputReference(DomainModel):
    """A declarative reference to an input required by a workflow."""

    input_name: WorkflowPlanningIdentifier


class WorkflowStepOutputReference(DomainModel):
    """A declarative reference to an output from another workflow step."""

    step_id: WorkflowPlanningIdentifier
    output_name: WorkflowPlanningIdentifier


class WorkflowInputBinding(DomainModel):
    """Binds an action parameter to a declared workflow value."""

    parameter: WorkflowPlanningIdentifier
    source: WorkflowInputSource


class WorkflowResultReference(DomainModel):
    """Identifies the workflow step output that represents the intended result."""

    step_id: WorkflowPlanningIdentifier
    output_name: WorkflowPlanningIdentifier


class WorkflowStepDefinition(DomainModel):
    """A logical unit of work in a workflow definition."""

    step_id: WorkflowStepId
    name: str
    description: str | None = None
    required_capabilities: tuple[CapabilityId, ...] = ()
    action_contract: WorkflowPlanningIdentifier | None = None
    input_bindings: tuple[WorkflowInputBinding, ...] = ()
    outputs: tuple[WorkflowPlanningIdentifier, ...] = ()
    metadata: Metadata = Field(default_factory=dict)


class WorkflowDefinition(DomainModel):
    """The versioned description of a workflow the Runtime can execute."""

    workflow_id: WorkflowId
    name: str
    version: str
    description: str | None = None
    steps: tuple[WorkflowStepDefinition, ...] = ()
    required_capabilities: tuple[CapabilityId, ...] = ()
    required_inputs: tuple[WorkflowPlanningIdentifier, ...] = ()
    result: WorkflowResultReference | None = None
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

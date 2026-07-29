"""Workflow definition, request, and result models."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, StrictBool, StringConstraints, model_validator

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


class WorkflowInputType(StrEnum):
    """Closed set of structural types accepted at a Workflow boundary."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NUMBER = "number"
    OBJECT = "object"
    ARRAY = "array"


class WorkflowInputDefinition(DomainModel):
    """One structurally typed external input declared by a Workflow."""

    name: WorkflowPlanningIdentifier
    type: WorkflowInputType
    required: StrictBool = True


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


class WorkflowIteration(DomainModel):
    """Expand one step input collection into deterministic invocations."""

    input_parameter: WorkflowPlanningIdentifier


class WorkflowStepDefinition(DomainModel):
    """A logical unit of work in a workflow definition."""

    step_id: WorkflowStepId
    name: str
    description: str | None = None
    required_capabilities: tuple[CapabilityId, ...] = ()
    action_contract: WorkflowPlanningIdentifier | None = None
    input_bindings: tuple[WorkflowInputBinding, ...] = ()
    outputs: tuple[WorkflowPlanningIdentifier, ...] = ()
    iteration: WorkflowIteration | None = None
    metadata: Metadata = Field(default_factory=dict)


class WorkflowDefinition(DomainModel):
    """The versioned description of a workflow the Runtime can execute."""

    workflow_id: WorkflowId
    name: str
    version: str
    description: str | None = None
    steps: tuple[WorkflowStepDefinition, ...] = ()
    required_capabilities: tuple[CapabilityId, ...] = ()
    inputs: tuple[WorkflowInputDefinition, ...] = ()
    result: WorkflowResultReference | None = None
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_unique_inputs(self) -> WorkflowDefinition:
        names = self.input_names
        if len(names) != len(set(names)):
            raise ValueError("Workflow input names must be unique")
        return self

    @property
    def input_names(self) -> tuple[WorkflowPlanningIdentifier, ...]:
        """Return every declared input name in definition order."""
        return tuple(definition.name for definition in self.inputs)

    @property
    def required_inputs(self) -> tuple[WorkflowPlanningIdentifier, ...]:
        """Return required input names in definition order."""
        return tuple(
            definition.name for definition in self.inputs if definition.required
        )


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

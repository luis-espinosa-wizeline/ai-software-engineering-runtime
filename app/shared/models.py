"""Shared primitives used by the Runtime domain."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
type Metadata = dict[str, JsonValue]

type RuntimeId = UUID
type WorkflowId = str
type WorkflowStepId = str
type CapabilityId = str


class DomainModel(BaseModel):
    """Base for immutable, strictly shaped domain values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

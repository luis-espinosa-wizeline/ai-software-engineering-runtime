"""Provider-neutral contracts for executable capabilities."""

from typing import Annotated, Protocol, runtime_checkable

from pydantic import Field, StringConstraints

from app.capabilities.artifact import Artifact
from app.shared import DomainModel, JsonValue

type ActionContractIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]


class CapabilityRequest(DomainModel):
    """Fully resolved inputs prepared for one capability invocation."""

    action_contract: ActionContractIdentifier
    inputs: dict[str, JsonValue] = Field(default_factory=dict)


class CapabilityResult(DomainModel):
    """Artifacts produced by one capability invocation."""

    artifacts: tuple[Artifact, ...] = Field(min_length=1)


@runtime_checkable
class Capability(Protocol):
    """Executable implementation of an action contract."""

    @property
    def action_contract(self) -> ActionContractIdentifier:
        """Identify the provider-neutral action implemented by this capability."""
        ...

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """Transform fully resolved inputs into artifacts."""
        ...

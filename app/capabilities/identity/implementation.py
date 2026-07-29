"""Minimal implementation used to validate the capability execution model."""

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)

IDENTITY = Capability(
    name="Identity",
    description="Return an input artifact payload unchanged.",
    category=CapabilityCategory.TRANSFORMATION,
    contract="Identity",
    version="1",
    input_artifacts=(
        ArtifactDefinition(name="value", description="Value to return."),
    ),
    output_artifacts=(
        ArtifactDefinition(name="result", description="Unchanged input value."),
    ),
    tags=("transformation", "identity"),
)


class IdentityCapabilityImplementation:
    """Return the input value as a result artifact without provider dependencies."""

    @property
    def capability(self) -> Capability:
        return IDENTITY

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        value = request.artifact("value")
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="result",
                    payload=value.payload,
                    metadata=value.metadata,
                ),
            )
        )

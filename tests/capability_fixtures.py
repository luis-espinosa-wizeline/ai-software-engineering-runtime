from app.capabilities import (
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
)


def capability(contract: str) -> Capability:
    """Build complete metadata for execution tests unrelated to catalog content."""
    return Capability(
        name=contract,
        description=f"Test Capability for {contract}.",
        category=CapabilityCategory.TRANSFORMATION,
        contract=contract,
        version="1",
        output_artifacts=(
            ArtifactDefinition(name="result", description="Test result."),
        ),
        tags=("test",),
    )

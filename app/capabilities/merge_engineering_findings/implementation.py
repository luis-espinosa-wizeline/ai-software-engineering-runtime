"""Deterministic aggregation of EngineeringFindings collections."""

from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
    EngineeringFindings,
)

MERGE_ENGINEERING_FINDINGS = Capability(
    name="MergeEngineeringFindings",
    description=(
        "Merge an ordered collection of engineering findings into one "
        "EngineeringFindings artifact."
    ),
    category=CapabilityCategory.ANALYSIS,
    contract="MergeEngineeringFindings",
    version="1",
    input_artifacts=(
        ArtifactDefinition(
            name="engineering_findings",
            description="Ordered collection of EngineeringFindings payloads.",
        ),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="engineering_findings",
            description="Unified EngineeringFindings payload.",
        ),
    ),
    tags=("analysis", "engineering-knowledge", "aggregation"),
)


class MergeEngineeringFindingsImplementation:
    """Concatenate findings without analyzing, sorting, or modifying them."""

    @property
    def capability(self) -> Capability:
        return MERGE_ENGINEERING_FINDINGS

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        collection = self._collection(request.artifact("engineering_findings"))
        merged = EngineeringFindings(
            findings=tuple(
                finding
                for findings in collection
                for finding in findings.findings
            )
        )
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="engineering_findings",
                    payload=merged.model_dump(mode="json"),
                ),
            )
        )

    @staticmethod
    def _collection(artifact: Artifact) -> tuple[EngineeringFindings, ...]:
        if not isinstance(artifact.payload, list):
            raise ValueError(
                "engineering_findings artifact must contain a list of "
                "EngineeringFindings"
            )
        try:
            return tuple(
                EngineeringFindings.model_validate(value)
                for value in artifact.payload
            )
        except ValidationError as error:
            raise ValueError(
                "engineering_findings artifact must contain only valid "
                "EngineeringFindings"
            ) from error

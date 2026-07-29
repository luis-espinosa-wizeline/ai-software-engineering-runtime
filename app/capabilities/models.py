"""Provider-neutral capability metadata, domain, and execution contracts."""

from enum import StrEnum
from typing import Annotated, Protocol, runtime_checkable

from pydantic import Field, StringConstraints, model_validator

from app.capabilities.artifact import Artifact, ArtifactName
from app.shared import DomainModel

type ActionContractIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
type CapabilityVersion = Annotated[str, StringConstraints(min_length=1)]


class CapabilityCategory(StrEnum):
    """Stable top-level groups in the public Capability Catalog."""

    REPOSITORY = "repository"
    ANALYSIS = "analysis"
    TRANSFORMATION = "transformation"
    PUBLISHING = "publishing"


class ArtifactDefinition(DomainModel):
    """A named artifact declared at a Capability boundary."""

    name: ArtifactName
    description: str

    @model_validator(mode="after")
    def _validate_description(self) -> ArtifactDefinition:
        if not self.description.strip():
            raise ValueError("Artifact description must not be blank")
        return self


class CapabilityMetadata(DomainModel):
    """Self-describing, provider-neutral metadata for one Capability."""

    name: str
    description: str
    category: CapabilityCategory
    contract: ActionContractIdentifier
    version: CapabilityVersion
    input_artifacts: tuple[ArtifactDefinition, ...] = ()
    output_artifacts: tuple[ArtifactDefinition, ...] = Field(min_length=1)
    tags: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_metadata(self) -> CapabilityMetadata:
        for field_name, value in (
            ("name", self.name),
            ("description", self.description),
            ("version", self.version),
        ):
            if not value.strip():
                raise ValueError(f"Capability {field_name} must not be blank")
        for collection_name, definitions in (
            ("input", self.input_artifacts),
            ("output", self.output_artifacts),
        ):
            names = tuple(definition.name for definition in definitions)
            if len(names) != len(set(names)):
                raise ValueError(
                    f"Capability {collection_name} artifact names must be unique"
                )
        if any(not tag.strip() for tag in self.tags):
            raise ValueError("Capability tags must not be blank")
        if len(self.tags) != len(set(self.tags)):
            raise ValueError("Capability tags must be unique")
        return self


class Capability(CapabilityMetadata):
    """A provider-neutral transformation the Runtime may request."""


class CapabilityRequest(DomainModel):
    """Named input artifacts prepared for one capability invocation."""

    capability: Capability
    artifacts: tuple[Artifact, ...] = ()

    @model_validator(mode="after")
    def _validate_unique_artifact_names(self) -> CapabilityRequest:
        names = tuple(artifact.name for artifact in self.artifacts)
        if len(names) != len(set(names)):
            raise ValueError("Capability input artifact names must be unique")
        return self

    def artifact(self, name: str) -> Artifact:
        """Return a named input artifact."""
        try:
            return next(artifact for artifact in self.artifacts if artifact.name == name)
        except StopIteration as error:
            raise ValueError(f"Input artifact {name!r} was not provided") from error


class CapabilityResult(DomainModel):
    """Artifacts produced by one capability invocation."""

    artifacts: tuple[Artifact, ...] = Field(min_length=1)


@runtime_checkable
class CapabilityImplementation(Protocol):
    """Executable realization of one provider-neutral Capability."""

    @property
    def capability(self) -> Capability:
        """Identify the Capability realized by this implementation."""
        ...

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """Transform input artifacts into output artifacts."""
        ...

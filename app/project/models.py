"""Immutable values produced by project discovery."""

from app.capabilities.models import CapabilityMetadata
from app.shared import DomainModel
from app.workflows.models import WorkflowDefinition


class CapabilityDescriptor(CapabilityMetadata):
    """Metadata for a capability that has been discovered but not loaded."""

    entrypoint: str


class Project(DomainModel):
    """An immutable snapshot of the resources discovered in a project directory."""

    name: str
    version: int
    workflows: tuple[WorkflowDefinition, ...] = ()
    capabilities: tuple[CapabilityDescriptor, ...] = ()

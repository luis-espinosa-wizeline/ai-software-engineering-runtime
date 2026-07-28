"""Workflow definition discovery abstractions."""

from collections.abc import Iterable
from typing import Protocol

from app.workflows.models import WorkflowDefinition


class WorkflowDiscovery(Protocol):
    """Source of workflow definitions for a registry."""

    def discover(self) -> tuple[WorkflowDefinition, ...]:
        """Return the workflow definitions exposed by this source."""
        ...


class InMemoryWorkflowDiscovery:
    """Discover workflow definitions from an immutable in-memory snapshot."""

    def __init__(self, workflows: Iterable[WorkflowDefinition]) -> None:
        self._workflows = tuple(workflows)

    def discover(self) -> tuple[WorkflowDefinition, ...]:
        """Return the snapshotted definitions in their supplied order."""
        return self._workflows

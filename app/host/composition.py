"""Capability implementation assembly boundary for Host executions."""

from typing import Protocol

from app.capabilities import CapabilityResolver
from app.host.events import HostEvent
from app.workflows import WorkflowDefinition


class CapabilityComposition(Protocol):
    """Produce the resolver configured for one Host execution."""

    def compose(
        self,
        event: HostEvent,
        workflow: WorkflowDefinition,
    ) -> CapabilityResolver:
        """Return concrete implementations behind a provider-neutral resolver."""
        ...


class InMemoryCapabilityComposition:
    """Return an explicitly supplied resolver for every execution."""

    def __init__(self, resolver: CapabilityResolver) -> None:
        self._resolver = resolver

    def compose(
        self,
        event: HostEvent,
        workflow: WorkflowDefinition,
    ) -> CapabilityResolver:
        """Return the configured resolver without loading plugins or providers."""
        return self._resolver

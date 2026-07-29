"""Provider-neutral workflow routing for normalized Host events."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

from pydantic import model_validator

from app.host.errors import UnsupportedHostEvent
from app.host.events import HostEvent
from app.shared import DomainModel, WorkflowId


class WorkflowRoute(DomainModel):
    """Exact workflow identity selected for one Host execution."""

    workflow_id: WorkflowId
    workflow_version: str

    @model_validator(mode="after")
    def _validate_identity(self) -> WorkflowRoute:
        if not self.workflow_id.strip():
            raise ValueError("Workflow route ID must not be blank")
        if not self.workflow_version.strip():
            raise ValueError("Workflow route version must not be blank")
        return self


class WorkflowSelector(Protocol):
    """Select one exact workflow route from a normalized Host event."""

    def select(self, event: HostEvent) -> WorkflowRoute:
        """Return the workflow route configured for the event."""
        ...


class InMemoryWorkflowSelector:
    """Select workflows from an immutable event-kind mapping."""

    def __init__(self, routes: Mapping[str, WorkflowRoute]) -> None:
        if any(not event_kind.strip() for event_kind in routes):
            raise ValueError("Workflow selector event kinds must not be blank")
        self._routes = MappingProxyType(dict(routes))

    def select(self, event: HostEvent) -> WorkflowRoute:
        """Return the exact configured route without inspecting workflow steps."""
        try:
            return self._routes[event.event_kind]
        except KeyError as error:
            raise UnsupportedHostEvent(event.event_kind) from error

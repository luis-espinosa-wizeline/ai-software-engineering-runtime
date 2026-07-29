"""Provider-neutral Runtime Host service-provider interface."""

from app.host.composition import (
    CapabilityComposition,
    InMemoryCapabilityComposition,
)
from app.host.context import ExecutionContextFactory
from app.host.coordinator import RuntimeHost
from app.host.errors import RuntimeHostError, UnsupportedHostEvent
from app.host.events import HostEvent
from app.host.results import HostExecutionResult
from app.host.routing import (
    InMemoryWorkflowSelector,
    WorkflowRoute,
    WorkflowSelector,
)

__all__ = [
    "CapabilityComposition",
    "ExecutionContextFactory",
    "HostEvent",
    "HostExecutionResult",
    "InMemoryCapabilityComposition",
    "InMemoryWorkflowSelector",
    "RuntimeHost",
    "RuntimeHostError",
    "UnsupportedHostEvent",
    "WorkflowRoute",
    "WorkflowSelector",
]

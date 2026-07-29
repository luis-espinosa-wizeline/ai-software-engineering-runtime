"""Failures raised at the provider-neutral Runtime Host boundary."""


class RuntimeHostError(Exception):
    """Base error for Runtime Host coordination failures."""


class UnsupportedHostEvent(RuntimeHostError):
    """Raised when no workflow route is configured for an event kind."""

    def __init__(self, event_kind: str) -> None:
        super().__init__(f"No workflow route is configured for event kind {event_kind!r}")

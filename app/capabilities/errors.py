"""Provider-neutral capability resolution errors."""


class CapabilityResolutionError(Exception):
    """Base error for deterministic capability resolution failures."""


class MissingCapability(CapabilityResolutionError):
    """Raised when no capability implements a requested Action Contract."""

    def __init__(self, action_contract: str) -> None:
        super().__init__(f"No capability implements Action Contract {action_contract!r}")


class DuplicateCapability(CapabilityResolutionError):
    """Raised when multiple implementations realize the same Action Contract."""

    def __init__(self, action_contract: str) -> None:
        super().__init__(f"Multiple capabilities implement Action Contract {action_contract!r}")

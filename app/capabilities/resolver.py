"""Minimal provider-neutral capability resolution."""

from collections.abc import Iterable
from types import MappingProxyType
from typing import Protocol

from app.capabilities.errors import DuplicateCapability, MissingCapability
from app.capabilities.models import Capability


class CapabilityResolver(Protocol):
    """Resolve executable capabilities by declared Action Contract."""

    def resolve(self, action_contract: str) -> Capability:
        """Return the capability implementing an Action Contract."""
        ...


class InMemoryCapabilityResolver:
    """Resolve a deterministic snapshot of capabilities by Action Contract."""

    def __init__(self, capabilities: Iterable[Capability]) -> None:
        by_action_contract: dict[str, Capability] = {}
        for capability in capabilities:
            if capability.action_contract in by_action_contract:
                raise DuplicateCapability(capability.action_contract)
            by_action_contract[capability.action_contract] = capability
        self._by_action_contract = MappingProxyType(by_action_contract)

    def resolve(self, action_contract: str) -> Capability:
        """Return the capability implementing an Action Contract."""
        try:
            return self._by_action_contract[action_contract]
        except KeyError as error:
            raise MissingCapability(action_contract) from error

"""Minimal provider-neutral capability resolution."""

from collections.abc import Iterable
from types import MappingProxyType
from typing import Protocol

from app.capabilities.errors import DuplicateCapability, MissingCapability
from app.capabilities.models import CapabilityImplementation


class CapabilityResolver(Protocol):
    """Resolve capability implementations by declared Action Contract."""

    def resolve(self, action_contract: str) -> CapabilityImplementation:
        """Return the implementation realizing an Action Contract."""
        ...


class InMemoryCapabilityResolver:
    """Resolve a deterministic snapshot of implementations by Action Contract."""

    def __init__(self, implementations: Iterable[CapabilityImplementation]) -> None:
        by_action_contract: dict[str, CapabilityImplementation] = {}
        for implementation in implementations:
            contract = implementation.capability.contract
            if contract in by_action_contract:
                raise DuplicateCapability(contract)
            by_action_contract[contract] = implementation
        self._by_action_contract = MappingProxyType(by_action_contract)

    def resolve(self, action_contract: str) -> CapabilityImplementation:
        """Return the implementation realizing an Action Contract."""
        try:
            return self._by_action_contract[action_contract]
        except KeyError as error:
            raise MissingCapability(action_contract) from error

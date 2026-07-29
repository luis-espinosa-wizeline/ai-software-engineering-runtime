"""Infrastructure boundary shared by repository Capability Implementations."""

from typing import Protocol

from app.shared import JsonValue


class RepositoryReader(Protocol):
    """Read provider-neutral repository information for an implementation."""

    def read_pull_request(
        self, repository: str, pull_request_number: int
    ) -> dict[str, JsonValue]:
        """Return provider-neutral pull-request data."""
        ...

    def read_changed_files(
        self, repository: str, pull_request_number: int
    ) -> list[JsonValue]:
        """Return provider-neutral changed-file data."""
        ...


__all__ = ["RepositoryReader"]

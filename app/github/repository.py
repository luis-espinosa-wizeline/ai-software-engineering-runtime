"""GitHub adapter for the provider-neutral RepositoryReader boundary."""

from pathlib import PurePosixPath

from app.github.client import GitHubClient
from app.github.errors import GitHubApiError
from app.shared import JsonValue


class GitHubRepositoryReader:
    """Expose readable pull-request data without leaking GitHub response objects."""

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    def read_pull_request(
        self,
        repository: str,
        pull_request_number: int,
    ) -> dict[str, JsonValue]:
        """Return the JSON-compatible pull-request response."""
        return self._client.pull_request(repository, pull_request_number)

    def read_changed_files(
        self,
        repository: str,
        pull_request_number: int,
    ) -> list[JsonValue]:
        """Return readable head-snapshot paths in GitHub's deterministic order."""
        paths: list[JsonValue] = []
        for item in self._client.changed_files(repository, pull_request_number):
            if item.get("status") == "removed":
                continue
            filename = item.get("filename")
            if not isinstance(filename, str) or not self._is_logical_path(filename):
                raise GitHubApiError(
                    "GitHub changed file did not contain a safe repository path"
                )
            paths.append(filename)
        return paths

    @staticmethod
    def _is_logical_path(value: str) -> bool:
        path = PurePosixPath(value)
        return bool(value) and not path.is_absolute() and ".." not in path.parts

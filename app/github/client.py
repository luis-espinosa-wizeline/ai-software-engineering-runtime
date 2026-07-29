"""Small authenticated GitHub API client used by repository adapters."""

from typing import Any
from urllib.parse import quote

import httpx

from app.github.errors import GitHubApiError


class GitHubClient:
    """Read pull-request repository data through an installation token."""

    def __init__(
        self,
        token: str,
        *,
        client: httpx.Client | None = None,
        api_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ) -> None:
        if not token.strip():
            raise ValueError("GitHub token must not be blank")
        self._token = token
        self._client = client
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout

    def pull_request(self, repository: str, number: int) -> dict[str, Any]:
        """Return one GitHub pull-request response."""
        payload = self._get_json(self._pull_request_path(repository, number))
        if not isinstance(payload, dict):
            raise GitHubApiError("GitHub pull-request response must be an object")
        return payload

    def changed_files(self, repository: str, number: int) -> list[dict[str, Any]]:
        """Return every changed-file response page in provider order."""
        path = self._pull_request_path(repository, number) + "/files"
        files: list[dict[str, Any]] = []
        page = 1
        while True:
            payload = self._get_json(path, params={"per_page": 100, "page": page})
            if not isinstance(payload, list) or any(
                not isinstance(item, dict) for item in payload
            ):
                raise GitHubApiError("GitHub changed-files response must be a list")
            files.extend(payload)
            if len(payload) < 100:
                return files
            page += 1

    def _get_json(
        self,
        path: str,
        *,
        params: dict[str, int] | None = None,
    ) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            if self._client is not None:
                response = self._client.get(path, headers=headers, params=params)
            else:
                response = httpx.get(
                    f"{self._api_url}{path}",
                    headers=headers,
                    params=params,
                    timeout=self._timeout,
                )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise GitHubApiError("GitHub repository data could not be read") from error

    @staticmethod
    def _pull_request_path(repository: str, number: int) -> str:
        parts = repository.split("/")
        if len(parts) != 2 or any(not part for part in parts):
            raise ValueError("repository must use the owner/name form")
        if number < 1:
            raise ValueError("pull-request number must be positive")
        owner, name = parts
        return (
            f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}/pulls/{number}"
        )

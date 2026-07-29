"""GitHub HTTP adapter behind the provider-neutral publishing boundary."""

from typing import Any
from urllib.parse import quote

import httpx

from app.capabilities.documents import MarkdownDocument
from app.capabilities.publishing import (
    InvalidPublicationResponse,
    PublicationAccessDenied,
    PublicationAuthenticationError,
    PublicationDestinationNotFound,
    PublicationResult,
    PublicationTransportError,
)


class GitHubCommentPublisher:
    """Publish one Markdown document as one GitHub pull-request comment."""

    def __init__(
        self,
        *,
        repository: str,
        pull_request_number: int,
        token: str,
        client: httpx.Client | None = None,
        api_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ) -> None:
        parts = repository.split("/")
        if len(parts) != 2 or any(not part for part in parts):
            raise ValueError("repository must use the owner/name form")
        if (
            not isinstance(pull_request_number, int)
            or isinstance(pull_request_number, bool)
            or pull_request_number < 1
        ):
            raise ValueError("pull_request_number must be a positive integer")
        if not token.strip():
            raise ValueError("GitHub token must be a non-empty string")

        owner, name = parts
        self._comments_path = (
            f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}"
            f"/issues/{pull_request_number}/comments"
        )
        self._token = token
        self._client = client
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout

    def publish(self, document: MarkdownDocument) -> PublicationResult:
        response = self._post(document.content)
        self._raise_for_status(response)
        publication_id = self._publication_id(response)
        return PublicationResult(
            success=True,
            publication_id=publication_id,
            destination="github-pull-request-comment",
        )

    def _post(self, content: str) -> httpx.Response:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            if self._client is not None:
                return self._client.post(
                    self._comments_path,
                    headers=headers,
                    json={"body": content},
                )
            return httpx.post(
                f"{self._api_url}{self._comments_path}",
                headers=headers,
                json={"body": content},
                timeout=self._timeout,
            )
        except httpx.HTTPError as error:
            raise PublicationTransportError(
                "The publication destination could not be reached"
            ) from error

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code in {200, 201}:
            return
        if response.status_code == 401:
            raise PublicationAuthenticationError("Publication authentication failed")
        if response.status_code == 403:
            raise PublicationAccessDenied("Publication access was denied")
        if response.status_code == 404:
            raise PublicationDestinationNotFound(
                "Publication destination was not found"
            )
        raise PublicationTransportError(
            f"Publication provider returned HTTP {response.status_code}"
        )

    @staticmethod
    def _publication_id(response: httpx.Response) -> str:
        try:
            payload: Any = response.json()
            publication_id = payload["id"]
            if not isinstance(publication_id, (str, int)) or isinstance(
                publication_id, bool
            ):
                raise TypeError
            value = str(publication_id)
            if not value:
                raise ValueError
            return value
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidPublicationResponse(
                "Publication provider response did not contain an identifier"
            ) from error

"""GitHub App authentication and installation-token resolution."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt

from app.github.errors import GitHubAuthenticationError

type Clock = Callable[[], datetime]


class GitHubAppAuthenticator:
    """Exchange a short-lived GitHub App JWT for an installation token."""

    def __init__(
        self,
        *,
        app_id: str,
        private_key: str,
        client: httpx.Client | None = None,
        api_url: str = "https://api.github.com",
        timeout: float = 30.0,
        clock: Clock | None = None,
    ) -> None:
        if not app_id.strip():
            raise ValueError("GitHub App ID must not be blank")
        if not private_key.strip():
            raise ValueError("GitHub private key must not be blank")
        self._app_id = app_id
        self._private_key = private_key
        self._client = client
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._clock = clock or (lambda: datetime.now(UTC))

    def installation_token(self, installation_id: int) -> str:
        """Return a token scoped to one positive GitHub App installation."""
        if installation_id < 1:
            raise ValueError("GitHub installation ID must be positive")
        app_jwt = self._app_jwt()
        path = f"/app/installations/{installation_id}/access_tokens"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {app_jwt}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            if self._client is not None:
                response = self._client.post(path, headers=headers)
            else:
                response = httpx.post(
                    f"{self._api_url}{path}",
                    headers=headers,
                    timeout=self._timeout,
                )
            response.raise_for_status()
            payload: Any = response.json()
            token = payload["token"]
            if not isinstance(token, str) or not token:
                raise TypeError
            return token
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise GitHubAuthenticationError(
                "GitHub App installation token could not be resolved"
            ) from error

    def _app_jwt(self) -> str:
        now = self._clock()
        claims = {
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + timedelta(minutes=9)).timestamp()),
            "iss": self._app_id,
        }
        try:
            return jwt.encode(claims, self._private_key, algorithm="RS256")
        except Exception as error:
            raise GitHubAuthenticationError(
                "GitHub App JWT could not be created"
            ) from error

from datetime import UTC, datetime

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.github import (
    GitHubApiError,
    GitHubAppAuthenticator,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubRepositoryReader,
)


def private_key() -> tuple[str, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private, public


def test_github_app_authenticator_exchanges_a_valid_short_lived_jwt() -> None:
    pem, public = private_key()
    observed: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(201, json={"token": "installation-token"})

    authenticator = GitHubAppAuthenticator(
        app_id="12345",
        private_key=pem,
        client=httpx.Client(
            base_url="https://api.github.test",
            transport=httpx.MockTransport(respond),
        ),
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )

    token = authenticator.installation_token(101)

    assert token == "installation-token"
    assert observed[0].url.path == "/app/installations/101/access_tokens"
    authorization = observed[0].headers["authorization"]
    claims = jwt.decode(
        authorization.removeprefix("Bearer "),
        public,
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["iss"] == "12345"
    assert claims["exp"] - claims["iat"] == 600


def test_github_app_authentication_failures_are_explicit() -> None:
    pem, _ = private_key()
    authenticator = GitHubAppAuthenticator(
        app_id="12345",
        private_key=pem,
        client=httpx.Client(
            base_url="https://api.github.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, json={"message": "bad"})
            ),
        ),
    )

    with pytest.raises(GitHubAuthenticationError, match="could not be resolved"):
        authenticator.installation_token(101)


def test_github_repository_reader_pages_and_returns_only_readable_safe_paths() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = request.url.params["page"]
        if page == "1":
            return httpx.Response(
                200,
                json=[
                    {"filename": f"src/file_{index}.py", "status": "modified"}
                    for index in range(100)
                ],
            )
        return httpx.Response(
            200,
            json=[
                {"filename": "src/final.py", "status": "added"},
                {"filename": "src/deleted.py", "status": "removed"},
            ],
        )

    reader = GitHubRepositoryReader(
        GitHubClient(
            "installation-token",
            client=httpx.Client(
                base_url="https://api.github.test",
                transport=httpx.MockTransport(respond),
            ),
        )
    )

    paths = reader.read_changed_files("example/runtime", 42)

    assert len(paths) == 101
    assert paths[-1] == "src/final.py"
    assert len(requests) == 2
    assert requests[0].headers["authorization"] == "Bearer installation-token"


def test_github_repository_reader_rejects_unsafe_provider_paths() -> None:
    reader = GitHubRepositoryReader(
        GitHubClient(
            "installation-token",
            client=httpx.Client(
                base_url="https://api.github.test",
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json=[{"filename": "../secret", "status": "modified"}],
                    )
                ),
            ),
        )
    )

    with pytest.raises(GitHubApiError, match="safe repository path"):
        reader.read_changed_files("example/runtime", 42)

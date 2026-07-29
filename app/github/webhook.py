"""Verification and normalization of GitHub pull-request webhooks."""

import hashlib
import hmac
import json
from typing import Any

from pydantic import model_validator

from app.github.errors import (
    InvalidGitHubEvent,
    InvalidWebhookSignature,
    UnsupportedGitHubEvent,
)
from app.shared import DomainModel

SUPPORTED_PULL_REQUEST_ACTIONS = frozenset({"opened", "reopened", "synchronize"})


class GitHubPullRequestEvent(DomainModel):
    """Validated GitHub facts required to prepare one Runtime execution."""

    delivery_id: str
    action: str
    repository: str
    pull_request_number: int
    installation_id: int
    head_sha: str
    clone_url: str

    @model_validator(mode="after")
    def _validate_values(self) -> GitHubPullRequestEvent:
        for field_name in (
            "delivery_id",
            "action",
            "repository",
            "head_sha",
            "clone_url",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be blank")
        if self.pull_request_number < 1:
            raise ValueError("pull_request_number must be positive")
        if self.installation_id < 1:
            raise ValueError("installation_id must be positive")
        return self


class GitHubWebhookVerifier:
    """Verify GitHub's HMAC-SHA256 signature over the exact request body."""

    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("GitHub webhook secret must not be empty")
        self._secret = secret.encode()

    def verify(self, body: bytes, signature: str | None) -> None:
        """Reject absent, malformed, or non-matching signatures."""
        expected = "sha256=" + hmac.new(
            self._secret,
            body,
            hashlib.sha256,
        ).hexdigest()
        if signature is None or not hmac.compare_digest(expected, signature):
            raise InvalidWebhookSignature("GitHub webhook signature is invalid")


def parse_pull_request_event(
    *,
    event_name: str | None,
    delivery_id: str | None,
    body: bytes,
) -> GitHubPullRequestEvent:
    """Map a supported GitHub payload into the Host's execution facts."""
    if event_name != "pull_request":
        raise UnsupportedGitHubEvent(
            f"GitHub event {event_name!r} is not supported"
        )
    if delivery_id is None or not delivery_id.strip():
        raise InvalidGitHubEvent("GitHub delivery identifier is required")

    try:
        payload: Any = json.loads(body)
        if not isinstance(payload, dict):
            raise TypeError
        action = payload["action"]
        repository = payload["repository"]["full_name"]
        number = payload["number"]
        installation_id = payload["installation"]["id"]
        head_sha = payload["pull_request"]["head"]["sha"]
        clone_url = payload["pull_request"]["head"]["repo"]["clone_url"]
        if action not in SUPPORTED_PULL_REQUEST_ACTIONS:
            raise UnsupportedGitHubEvent(
                f"Pull-request action {action!r} is not supported"
            )
        return GitHubPullRequestEvent(
            delivery_id=delivery_id,
            action=action,
            repository=repository,
            pull_request_number=number,
            installation_id=installation_id,
            head_sha=head_sha,
            clone_url=clone_url,
        )
    except UnsupportedGitHubEvent:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidGitHubEvent(
            "GitHub pull-request payload is missing required execution data"
        ) from error

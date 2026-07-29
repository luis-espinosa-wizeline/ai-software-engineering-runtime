import hashlib
import hmac
import json

import pytest

from app.github import (
    InvalidGitHubEvent,
    InvalidWebhookSignature,
    UnsupportedGitHubEvent,
)
from app.github.webhook import GitHubWebhookVerifier, parse_pull_request_event


def pull_request_payload(action: str = "synchronize") -> dict[str, object]:
    return {
        "action": action,
        "number": 42,
        "installation": {"id": 101},
        "repository": {
            "full_name": "example/runtime",
            "clone_url": "https://github.com/example/runtime.git",
        },
        "pull_request": {
            "head": {
                "sha": "a" * 40,
                "repo": {
                    "clone_url": "https://github.com/contributor/runtime.git"
                },
            }
        },
    }


def test_webhook_verifier_accepts_only_matching_raw_body_signature() -> None:
    body = b'{"action":"synchronize"}'
    signature = "sha256=" + hmac.new(
        b"webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    verifier = GitHubWebhookVerifier("webhook-secret")

    verifier.verify(body, signature)

    with pytest.raises(InvalidWebhookSignature):
        verifier.verify(body + b" ", signature)
    with pytest.raises(InvalidWebhookSignature):
        verifier.verify(body, None)


def test_pull_request_event_is_normalized_and_uses_exact_head_repository() -> None:
    event = parse_pull_request_event(
        event_name="pull_request",
        delivery_id="delivery-1",
        body=json.dumps(pull_request_payload()).encode(),
    )

    assert event.repository == "example/runtime"
    assert event.pull_request_number == 42
    assert event.installation_id == 101
    assert event.head_sha == "a" * 40
    assert event.clone_url == "https://github.com/contributor/runtime.git"


@pytest.mark.parametrize("action", ["closed", "labeled", "edited"])
def test_pull_request_event_rejects_unsupported_actions(action: str) -> None:
    with pytest.raises(UnsupportedGitHubEvent, match=action):
        parse_pull_request_event(
            event_name="pull_request",
            delivery_id="delivery-1",
            body=json.dumps(pull_request_payload(action)).encode(),
        )


def test_webhook_parser_rejects_other_events_and_malformed_payloads() -> None:
    with pytest.raises(UnsupportedGitHubEvent, match="push"):
        parse_pull_request_event(
            event_name="push",
            delivery_id="delivery-1",
            body=b"{}",
        )
    with pytest.raises(InvalidGitHubEvent, match="delivery"):
        parse_pull_request_event(
            event_name="pull_request",
            delivery_id=None,
            body=b"{}",
        )
    with pytest.raises(InvalidGitHubEvent, match="required execution data"):
        parse_pull_request_event(
            event_name="pull_request",
            delivery_id="delivery-1",
            body=b"not-json",
        )

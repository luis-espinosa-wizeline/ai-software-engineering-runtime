from unittest.mock import Mock
from uuid import UUID

from fastapi.testclient import TestClient

from app.capabilities import Artifact
from app.github import GitHubRuntimeHost
from app.github.errors import InvalidWebhookSignature
from app.host import HostExecutionResult
from app.main import app


def test_read_runtime_info() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "AI Software Engineering Runtime",
        "version": "0.1.0",
    }


def test_github_webhook_endpoint_returns_host_execution_identity() -> None:
    host = Mock(spec=GitHubRuntimeHost)
    host.handle.return_value = HostExecutionResult(
        execution_id=UUID("00000000-0000-0000-0000-000000000011"),
        workflow_id="pull-request-engineering-review",
        workflow_version="1",
        success=True,
        final_artifact=Artifact(
            name="publication_result",
            payload={"success": True},
        ),
    )
    app.state.github_runtime_host = host
    client = TestClient(app)

    response = client.post(
        "/github/webhooks",
        content=b'{"event":"body"}',
        headers={
            "X-Hub-Signature-256": "sha256=signature",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "execution_id": "00000000-0000-0000-0000-000000000011",
        "workflow_id": "pull-request-engineering-review",
        "workflow_version": "1",
        "result_artifact": "publication_result",
    }


def test_github_webhook_endpoint_maps_signature_failure() -> None:
    host = Mock(spec=GitHubRuntimeHost)
    host.handle.side_effect = InvalidWebhookSignature("invalid signature")
    app.state.github_runtime_host = host
    client = TestClient(app)

    response = client.post("/github/webhooks", content=b"{}")

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}

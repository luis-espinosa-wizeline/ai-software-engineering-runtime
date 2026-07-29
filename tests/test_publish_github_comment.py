import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.capabilities import (
    Artifact,
    CapabilityRequest,
    InvalidPublicationResponse,
    MarkdownDocument,
    PublicationAccessDenied,
    PublicationAuthenticationError,
    PublicationDestinationNotFound,
    PublicationResult,
    PublicationTransportError,
)
from app.capabilities.analyze_source_code import (
    AnalyzeSourceCodeOllamaImplementation,
)
from app.capabilities.generate_markdown import GenerateMarkdownImplementation
from app.capabilities.publish_github_comment import (
    GitHubCommentPublisher,
    PublishGitHubCommentImplementation,
)
from app.capabilities.read_file import ReadFileImplementation


class RecordingPublisher:
    def __init__(self, result: PublicationResult | None = None) -> None:
        self.documents: list[MarkdownDocument] = []
        self._result = result or PublicationResult(
            success=True,
            publication_id="comment-42",
            destination="test-pull-request-comment",
        )

    def publish(self, document: MarkdownDocument) -> PublicationResult:
        self.documents.append(document)
        return self._result


def publication_request(
    implementation: PublishGitHubCommentImplementation,
    document: MarkdownDocument,
) -> CapabilityRequest:
    return CapabilityRequest(
        capability=implementation.capability,
        artifacts=(
            Artifact(name="markdown", payload=document.model_dump(mode="json")),
        ),
    )


def test_capability_publishes_exact_document_and_returns_neutral_result() -> None:
    publisher = RecordingPublisher()
    implementation = PublishGitHubCommentImplementation(publisher)
    document = MarkdownDocument(
        content="## Engineering Analysis\n\nExact content.  \n"
    )

    result = implementation.execute(publication_request(implementation, document))

    assert publisher.documents == [document]
    assert result.artifacts == (
        Artifact(
            name="publication_result",
            payload={
                "success": True,
                "publication_id": "comment-42",
                "destination": "test-pull-request-comment",
            },
        ),
    )


def test_capability_can_report_unsuccessful_publication_result() -> None:
    publisher = RecordingPublisher(
        PublicationResult(
            success=False,
            publication_id=None,
            destination="temporarily-unavailable-destination",
        )
    )
    implementation = PublishGitHubCommentImplementation(publisher)

    result = implementation.execute(
        publication_request(implementation, MarkdownDocument(content="Document"))
    )

    assert result.artifacts[0].payload == {
        "success": False,
        "publication_id": None,
        "destination": "temporarily-unavailable-destination",
    }


@pytest.mark.parametrize(
    "payload",
    [
        "raw Markdown is not the document contract",
        {"content": ""},
        {"body": "wrong field"},
    ],
)
def test_capability_rejects_invalid_markdown_document(payload: Any) -> None:
    implementation = PublishGitHubCommentImplementation(RecordingPublisher())
    request = CapabilityRequest(
        capability=implementation.capability,
        artifacts=(Artifact(name="markdown", payload=payload),),
    )

    with pytest.raises(ValueError, match="valid MarkdownDocument"):
        implementation.execute(request)


def test_github_adapter_posts_one_comment_without_modification() -> None:
    observed: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(201, json={"id": 987654})

    client = httpx.Client(
        base_url="https://api.github.test",
        transport=httpx.MockTransport(respond),
    )
    publisher = GitHubCommentPublisher(
        repository="example/runtime",
        pull_request_number=42,
        token="secret-token",
        client=client,
    )
    content = "## Analysis\n\nPreserve this exactly.  \n"

    result = publisher.publish(MarkdownDocument(content=content))

    assert result == PublicationResult(
        success=True,
        publication_id="987654",
        destination="github-pull-request-comment",
    )
    assert len(observed) == 1
    request = observed[0]
    assert request.url.path == "/repos/example/runtime/issues/42/comments"
    assert json.loads(request.content) == {"body": content}
    assert request.headers["authorization"] == "Bearer secret-token"
    assert request.headers["x-github-api-version"] == "2022-11-28"


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, PublicationAuthenticationError),
        (403, PublicationAccessDenied),
        (404, PublicationDestinationNotFound),
        (500, PublicationTransportError),
    ],
)
def test_github_adapter_maps_provider_failures_to_delivery_errors(
    status: int,
    error_type: type[Exception],
) -> None:
    client = httpx.Client(
        base_url="https://api.github.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json={"message": "failure"})
        ),
    )
    publisher = GitHubCommentPublisher(
        repository="example/runtime",
        pull_request_number=42,
        token="secret-token",
        client=client,
    )

    with pytest.raises(error_type):
        publisher.publish(MarkdownDocument(content="Document"))


def test_github_adapter_rejects_unexpected_success_response() -> None:
    publisher = GitHubCommentPublisher(
        repository="example/runtime",
        pull_request_number=42,
        token="secret-token",
        client=httpx.Client(
            base_url="https://api.github.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(201, json={"url": "missing id"})
            ),
        ),
    )

    with pytest.raises(InvalidPublicationResponse):
        publisher.publish(MarkdownDocument(content="Document"))


def test_github_adapter_maps_network_failure() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    publisher = GitHubCommentPublisher(
        repository="example/runtime",
        pull_request_number=42,
        token="secret-token",
        client=httpx.Client(
            base_url="https://api.github.test",
            transport=httpx.MockTransport(fail),
        ),
    )

    with pytest.raises(PublicationTransportError):
        publisher.publish(MarkdownDocument(content="Document"))


def test_complete_knowledge_pipeline_composes_into_delivery(tmp_path: Path) -> None:
    source_path = tmp_path / "service.py"
    source_path.write_text("def work():\n    return None\n", encoding="utf-8")
    read_file = ReadFileImplementation()
    source = read_file.execute(
        CapabilityRequest(
            capability=read_file.capability,
            artifacts=(Artifact(name="path", payload=str(source_path)),),
        )
    )
    ollama_output = {
        "findings": [
            {
                "summary": "Missing return contract",
                "source_file": "model.py",
                "severity": "low",
                "confidence": 0.75,
                "category": "maintainability",
                "explanation": "The function contract is not documented.",
                "recommendation": "Document the expected return value.",
            }
        ]
    }
    analyzer = AnalyzeSourceCodeOllamaImplementation(
        "test-model",
        client=httpx.Client(
            base_url="http://ollama.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(ollama_output),
                        }
                    },
                )
            ),
        ),
    )
    findings = analyzer.execute(
        CapabilityRequest(
            capability=analyzer.capability,
            artifacts=source.artifacts,
        )
    )
    generator = GenerateMarkdownImplementation()
    markdown = generator.execute(
        CapabilityRequest(
            capability=generator.capability,
            artifacts=findings.artifacts,
        )
    )
    publisher = RecordingPublisher()
    delivery = PublishGitHubCommentImplementation(publisher)

    result = delivery.execute(
        CapabilityRequest(
            capability=delivery.capability,
            artifacts=markdown.artifacts,
        )
    )

    assert len(publisher.documents) == 1
    assert "Missing return contract" in publisher.documents[0].content
    assert "Document the expected return value" in publisher.documents[0].content
    assert result.artifacts[0].name == "publication_result"

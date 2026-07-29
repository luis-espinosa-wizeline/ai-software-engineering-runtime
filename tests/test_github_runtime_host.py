import hashlib
import hmac
import json
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import Mock

import httpx

from app.capabilities import (
    Artifact,
    CapabilityRequest,
    InMemoryCapabilityResolver,
    PublicationResult,
)
from app.capabilities.analyze_source_code import (
    AnalyzeSourceCodeOllamaImplementation,
)
from app.capabilities.documents import MarkdownDocument
from app.capabilities.generate_markdown import GenerateMarkdownImplementation
from app.capabilities.merge_engineering_findings import (
    MergeEngineeringFindingsImplementation,
)
from app.capabilities.publish_github_comment import (
    PublishGitHubCommentImplementation,
)
from app.capabilities.publishing import EngineeringPublisher
from app.capabilities.read_changed_files import ReadChangedFilesImplementation
from app.capabilities.read_file import ReadFileImplementation
from app.capabilities.repository import RepositoryReader
from app.github import (
    GitHubAppAuthenticator,
    GitHubCapabilityComposition,
    GitHubHostSettings,
    GitHubPullRequestEvent,
    GitHubRuntimeHost,
    RepositoryWorkspace,
    WorkspaceManager,
)
from app.host import (
    CapabilityComposition,
    HostEvent,
    InMemoryCapabilityComposition,
)
from app.shared import JsonValue
from app.workflows import WorkflowDefinition

SHA = "a" * 40


class ChangedFilesReader(RepositoryReader):
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def read_pull_request(
        self,
        repository: str,
        pull_request_number: int,
    ) -> dict[str, JsonValue]:
        raise AssertionError("Pull-request metadata is not used")

    def read_changed_files(
        self,
        repository: str,
        pull_request_number: int,
    ) -> list[JsonValue]:
        return list(self._paths)


class RecordingPublisher(EngineeringPublisher):
    def __init__(self) -> None:
        self.documents: list[MarkdownDocument] = []

    def publish(self, document: MarkdownDocument) -> PublicationResult:
        self.documents.append(document)
        return PublicationResult(
            success=True,
            publication_id="comment-9001",
            destination="github-pull-request-comment",
        )


def webhook_body() -> bytes:
    return json.dumps(
        {
            "action": "synchronize",
            "number": 42,
            "installation": {"id": 101},
            "repository": {
                "full_name": "example/runtime",
                "clone_url": "https://github.com/example/runtime.git",
            },
            "pull_request": {
                "head": {
                    "sha": SHA,
                    "repo": {
                        "clone_url": "https://github.com/example/runtime.git"
                    },
                }
            },
        }
    ).encode()


def test_production_composition_uses_workspace_scoped_read_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src" / "service.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    workspace = RepositoryWorkspace(tmp_path, SHA, 1_000)
    composition = GitHubCapabilityComposition(
        repository="example/runtime",
        pull_request_number=42,
        installation_token="token",
        workspace=workspace,
        ollama_model="test-model",
        github_api_url="https://api.github.test",
        ollama_base_url="http://ollama.test",
    )
    event = HostEvent(
        event_kind="github.pull_request",
        inputs={"repository": "example/runtime", "pull_request_number": 42},
    )

    resolver = composition.compose(
        event,
        WorkflowDefinition(workflow_id="review", name="Review", version="1"),
    )
    read_file = resolver.resolve("ReadFile")
    result = read_file.execute(
        CapabilityRequest(
            capability=read_file.capability,
            artifacts=(Artifact(name="path", payload="src/service.py"),),
        )
    )

    assert result.artifacts[0].payload == {
        "path": "src/service.py",
        "content": "VALUE = 1\n",
    }
    assert {
        resolver.resolve(contract).capability.contract
        for contract in (
            "ReadChangedFiles",
            "ReadFile",
            "AnalyzeSourceCode",
            "MergeEngineeringFindings",
            "GenerateMarkdown",
            "PublishGitHubComment",
        )
    } == {
        "ReadChangedFiles",
        "ReadFile",
        "AnalyzeSourceCode",
        "MergeEngineeringFindings",
        "GenerateMarkdown",
        "PublishGitHubComment",
    }


def test_github_runtime_host_executes_pipeline_and_cleans_workspace(
    tmp_path: Path,
) -> None:
    body = webhook_body()
    signature = "sha256=" + hmac.new(
        b"webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    workspace_roots: list[Path] = []

    def prepare_checkout(
        command: list[str],
        workspace: Path,
        environment: Mapping[str, str],
    ) -> None:
        if command[:2] == ["git", "checkout"]:
            workspace_roots.append(workspace)
            (workspace / "first.py").write_text("FIRST = unsafe()\n", encoding="utf-8")
            (workspace / "second.py").write_text(
                "SECOND = unsafe()\n",
                encoding="utf-8",
            )

    authenticator = Mock(spec=GitHubAppAuthenticator)
    authenticator.installation_token.return_value = "installation-token"
    publisher = RecordingPublisher()
    analyzed: list[str] = []

    def analyze(request: httpx.Request) -> httpx.Response:
        prompt = json.loads(request.content)["messages"][1]["content"]
        marker = "FIRST" if "FIRST = unsafe()" in prompt else "SECOND"
        analyzed.append(marker)
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "findings": [
                                {
                                    "summary": f"{marker} finding",
                                    "source_file": "model.py",
                                    "severity": "high",
                                    "confidence": 0.9,
                                    "category": "reliability",
                                    "explanation": "Unsafe operation.",
                                    "recommendation": "Use a safe operation.",
                                }
                            ]
                        }
                    )
                }
            },
        )

    def composition_factory(
        event: GitHubPullRequestEvent,
        token: str,
        workspace: RepositoryWorkspace,
        settings: GitHubHostSettings,
    ) -> CapabilityComposition:
        analyzer = AnalyzeSourceCodeOllamaImplementation(
            "test-model",
            client=httpx.Client(
                base_url="http://ollama.test",
                transport=httpx.MockTransport(analyze),
            ),
        )
        resolver = InMemoryCapabilityResolver(
            (
                ReadChangedFilesImplementation(
                    ChangedFilesReader(["first.py", "second.py"])
                ),
                ReadFileImplementation(workspace.read_text),
                analyzer,
                MergeEngineeringFindingsImplementation(),
                GenerateMarkdownImplementation(),
                PublishGitHubCommentImplementation(publisher),
            )
        )
        return InMemoryCapabilityComposition(resolver)

    settings = GitHubHostSettings(
        github_app_id="123",
        github_private_key="private-key",
        github_webhook_secret="webhook-secret",
        ollama_model="test-model",
        project_root=Path(__file__).parents[1],
        workspace_base=tmp_path,
    )
    host = GitHubRuntimeHost(
        settings,
        authenticator=authenticator,
        workspace_manager=WorkspaceManager(
            base_directory=tmp_path,
            command_runner=prepare_checkout,
        ),
        composition_factory=composition_factory,
    )

    result = host.handle(
        body=body,
        signature=signature,
        event_name="pull_request",
        delivery_id="delivery-1",
    )

    authenticator.installation_token.assert_called_once_with(101)
    assert analyzed == ["FIRST", "SECOND"]
    assert result.final_artifact.name == "publication_result"
    assert (
        PublicationResult.model_validate(result.final_artifact.payload).publication_id
        == "comment-9001"
    )
    assert len(publisher.documents) == 1
    assert publisher.documents[0].content.count("### Finding ") == 2
    assert workspace_roots and all(not path.exists() for path in workspace_roots)

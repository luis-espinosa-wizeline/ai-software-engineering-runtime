import json
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from app.capabilities import (
    InMemoryCapabilityResolver,
    PublicationResult,
)
from app.capabilities.analyze_source_code import (
    AnalyzeSourceCodeOllamaImplementation,
)
from app.capabilities.generate_markdown import GenerateMarkdownImplementation
from app.capabilities.merge_engineering_findings import (
    MergeEngineeringFindingsImplementation,
)
from app.capabilities.publish_github_comment import (
    GitHubCommentPublisher,
    PublishGitHubCommentImplementation,
)
from app.capabilities.read_changed_files import ReadChangedFilesImplementation
from app.capabilities.read_file import ReadFileImplementation
from app.execution import ExecutionContext, ExecutionEngine, ExecutionPlanner
from app.project import ProjectLoader
from app.shared import JsonValue
from app.workflows import WorkflowRegistry

EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000009")


class PullRequestRepositoryReader:
    def __init__(self, changed_files: list[str]) -> None:
        self._changed_files = changed_files
        self.requests: list[tuple[str, int]] = []

    def read_pull_request(
        self,
        repository: str,
        pull_request_number: int,
    ) -> dict[str, JsonValue]:
        raise AssertionError("The workflow does not request pull-request metadata")

    def read_changed_files(
        self,
        repository: str,
        pull_request_number: int,
    ) -> list[JsonValue]:
        self.requests.append((repository, pull_request_number))
        return list(self._changed_files)


def test_discovered_pull_request_workflow_executes_complete_pipeline(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("FIRST_VALUE = unsafe_call()\n", encoding="utf-8")
    second.write_text("SECOND_VALUE = unsafe_call()\n", encoding="utf-8")
    repository_reader = PullRequestRepositoryReader([str(first), str(second)])
    analyzed: list[str] = []

    def analyze(request: httpx.Request) -> httpx.Response:
        body: dict[str, Any] = json.loads(request.content)
        prompt: str = body["messages"][1]["content"]
        marker = "FIRST" if "FIRST_VALUE" in prompt else "SECOND"
        analyzed.append(marker)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "findings": [
                                {
                                    "summary": f"{marker} unchecked result",
                                    "source_file": "model-supplied.py",
                                    "start_line": 1,
                                    "end_line": 1,
                                    "rule_id": "reliability.unchecked-result",
                                    "severity": "high",
                                    "confidence": 0.95,
                                    "category": "reliability",
                                    "explanation": (
                                        f"The {marker} result is not checked for failure."
                                    ),
                                    "recommendation": "Check the result before use.",
                                }
                            ]
                        }
                    ),
                }
            },
        )

    published_requests: list[httpx.Request] = []

    def publish(request: httpx.Request) -> httpx.Response:
        published_requests.append(request)
        return httpx.Response(201, json={"id": 9001})

    analyzer = AnalyzeSourceCodeOllamaImplementation(
        "test-model",
        client=httpx.Client(
            base_url="http://ollama.test",
            transport=httpx.MockTransport(analyze),
        ),
    )
    publisher = GitHubCommentPublisher(
        repository="example/runtime",
        pull_request_number=42,
        token="test-token",
        client=httpx.Client(
            base_url="https://api.github.test",
            transport=httpx.MockTransport(publish),
        ),
    )
    resolver = InMemoryCapabilityResolver(
        (
            ReadChangedFilesImplementation(repository_reader),
            ReadFileImplementation(),
            analyzer,
            MergeEngineeringFindingsImplementation(),
            GenerateMarkdownImplementation(),
            PublishGitHubCommentImplementation(publisher),
        )
    )

    project_root = Path(__file__).parents[1]
    project = ProjectLoader().load(project_root)
    workflow = WorkflowRegistry(project.workflows).get(
        "pull-request-engineering-review",
        "1",
    )
    plan = ExecutionPlanner().plan(workflow)
    context = ExecutionContext(
        execution_id=EXECUTION_ID,
        plan_id=plan.plan_id,
        inputs={
            "repository": "example/runtime",
            "pull_request_number": 42,
        },
    )

    result = ExecutionEngine(resolver).execute(plan, context)

    assert repository_reader.requests == [("example/runtime", 42)]
    assert analyzed == ["FIRST", "SECOND"]
    assert result.name == "publication_result"
    assert PublicationResult.model_validate(result.payload) == PublicationResult(
        success=True,
        publication_id="9001",
        destination="github-pull-request-comment",
    )
    assert len(published_requests) == 1
    publication = published_requests[0]
    assert publication.url.path == "/repos/example/runtime/issues/42/comments"
    body = json.loads(publication.content)["body"]
    assert body.count("### Finding ") == 2
    assert body.index("FIRST unchecked result") < body.index(
        "SECOND unchecked result"
    )
    assert "first\\.py" in body
    assert "second\\.py" in body
    assert body.count("- **Lines:** 1-1") == 2
    assert "model\\-supplied\\.py" not in body

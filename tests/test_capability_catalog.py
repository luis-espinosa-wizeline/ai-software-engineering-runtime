from pathlib import Path

import pytest
from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityImplementation,
    CapabilityLoader,
    CapabilityRequest,
    MarkdownDocument,
    PublicationResult,
)
from app.capabilities.analyze_source_code import AnalyzeSourceCodeOllamaImplementation
from app.capabilities.generate_markdown import GenerateMarkdownImplementation
from app.capabilities.merge_engineering_findings import (
    MergeEngineeringFindingsImplementation,
)
from app.capabilities.publish_github_comment import PublishGitHubCommentImplementation
from app.capabilities.read_changed_files import ReadChangedFilesImplementation
from app.capabilities.read_file import ReadFileImplementation
from app.capabilities.read_pull_request import ReadPullRequestImplementation
from app.project import CapabilityDescriptor
from app.shared import JsonValue


class StubRepositoryReader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def read_pull_request(
        self, repository: str, pull_request_number: int
    ) -> dict[str, JsonValue]:
        self.calls.append(("pull_request", repository, pull_request_number))
        return {
            "repository": repository,
            "number": pull_request_number,
            "title": "Add capability catalog",
            "state": "open",
        }

    def read_changed_files(
        self, repository: str, pull_request_number: int
    ) -> list[JsonValue]:
        self.calls.append(("changed_files", repository, pull_request_number))
        return [
            {"path": "app/main.py", "status": "modified"},
            {"path": "README.md", "status": "added"},
        ]


class StubPublisher:
    def publish(self, document: MarkdownDocument) -> PublicationResult:
        return PublicationResult(
            success=True,
            publication_id="test",
            destination="test",
        )


def request(
    implementation: CapabilityImplementation,
    *artifacts: Artifact,
) -> CapabilityRequest:
    return CapabilityRequest(
        capability=implementation.capability,
        artifacts=artifacts,
    )


def test_capability_metadata_is_complete_immutable_and_validated() -> None:
    metadata = Capability(
        name="Example",
        description="Perform an example engineering transformation.",
        category=CapabilityCategory.TRANSFORMATION,
        contract="Example",
        version="1",
        input_artifacts=(
            ArtifactDefinition(name="source", description="Input source."),
        ),
        output_artifacts=(
            ArtifactDefinition(name="result", description="Output result."),
        ),
        tags=("example", "transformation"),
    )

    assert metadata.category is CapabilityCategory.TRANSFORMATION
    assert metadata.input_artifacts[0].name == "source"
    with pytest.raises(ValidationError):
        metadata.version = "2"

    with pytest.raises(ValidationError, match="output artifact names must be unique"):
        Capability(
            name="DuplicateOutputs",
            description="Invalid duplicate outputs.",
            category=CapabilityCategory.ANALYSIS,
            contract="DuplicateOutputs",
            version="1",
            output_artifacts=(
                ArtifactDefinition(name="result", description="First."),
                ArtifactDefinition(name="result", description="Second."),
            ),
            tags=("invalid",),
        )


def test_initial_catalog_is_discoverable_without_importing_implementations() -> None:
    capabilities_directory = Path(__file__).parents[1] / "app" / "capabilities"

    catalog = CapabilityLoader().load(capabilities_directory)

    assert tuple(descriptor.name for descriptor in catalog) == (
        "AnalyzeSourceCode",
        "GenerateMarkdown",
        "MergeEngineeringFindings",
        "PublishGitHubComment",
        "ReadChangedFiles",
        "ReadFile",
        "ReadPullRequest",
    )
    assert {descriptor.category for descriptor in catalog} == {
        CapabilityCategory.ANALYSIS,
        CapabilityCategory.PUBLISHING,
        CapabilityCategory.REPOSITORY,
        CapabilityCategory.TRANSFORMATION,
    }
    assert all(descriptor.description for descriptor in catalog)
    assert all(descriptor.version == "1" for descriptor in catalog)
    assert all(descriptor.output_artifacts for descriptor in catalog)
    assert all(descriptor.tags for descriptor in catalog)


@pytest.mark.parametrize(
    ("implementation", "catalog_name"),
    [
        (
            AnalyzeSourceCodeOllamaImplementation("test-model"),
            "AnalyzeSourceCode",
        ),
        (GenerateMarkdownImplementation(), "GenerateMarkdown"),
        (
            MergeEngineeringFindingsImplementation(),
            "MergeEngineeringFindings",
        ),
        (
            PublishGitHubCommentImplementation(StubPublisher()),
            "PublishGitHubComment",
        ),
        (ReadPullRequestImplementation(StubRepositoryReader()), "ReadPullRequest"),
        (ReadChangedFilesImplementation(StubRepositoryReader()), "ReadChangedFiles"),
        (ReadFileImplementation(lambda path: path.name), "ReadFile"),
    ],
)
def test_implementation_metadata_matches_catalog(
    implementation: CapabilityImplementation,
    catalog_name: str,
) -> None:
    directory = Path(__file__).parents[1] / "app" / "capabilities"
    descriptors = {
        descriptor.name: descriptor for descriptor in CapabilityLoader().load(directory)
    }
    descriptor: CapabilityDescriptor = descriptors[catalog_name]

    assert descriptor.model_dump(exclude={"entrypoint"}) == (
        implementation.capability.model_dump()
    )


def test_read_pull_request_produces_provider_neutral_artifact() -> None:
    reader = StubRepositoryReader()
    implementation = ReadPullRequestImplementation(reader)

    result = implementation.execute(
        request(
            implementation,
            Artifact(name="repository", payload="example/runtime"),
            Artifact(name="pull_request_number", payload=42),
        )
    )

    assert reader.calls == [("pull_request", "example/runtime", 42)]
    assert result.artifacts == (
        Artifact(
            name="pull_request",
            payload={
                "repository": "example/runtime",
                "number": 42,
                "title": "Add capability catalog",
                "state": "open",
            },
        ),
    )


def test_read_changed_files_produces_composable_artifact() -> None:
    reader = StubRepositoryReader()
    implementation = ReadChangedFilesImplementation(reader)

    result = implementation.execute(
        request(
            implementation,
            Artifact(name="repository", payload="example/runtime"),
            Artifact(name="pull_request_number", payload=42),
        )
    )

    assert reader.calls == [("changed_files", "example/runtime", 42)]
    assert result.artifacts[0].name == "changed_files"
    assert result.artifacts[0].payload == [
        {"path": "app/main.py", "status": "modified"},
        {"path": "README.md", "status": "added"},
    ]


def test_read_file_reads_utf8_content(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text('message = "área"\n', encoding="utf-8")
    implementation = ReadFileImplementation()

    result = implementation.execute(
        request(implementation, Artifact(name="path", payload=str(source)))
    )

    assert result.artifacts == (
        Artifact(
            name="SourceCode",
            payload={"path": str(source), "content": 'message = "área"\n'},
        ),
    )


@pytest.mark.parametrize(
    ("implementation", "artifacts", "message"),
    [
        (
            ReadPullRequestImplementation(StubRepositoryReader()),
            (
                Artifact(name="repository", payload="example/runtime"),
                Artifact(name="pull_request_number", payload=0),
            ),
            "positive integer",
        ),
        (
            ReadChangedFilesImplementation(StubRepositoryReader()),
            (
                Artifact(name="repository", payload=""),
                Artifact(name="pull_request_number", payload=1),
            ),
            "non-empty string",
        ),
        (
            ReadFileImplementation(),
            (Artifact(name="path", payload=42),),
            "non-empty string",
        ),
    ],
)
def test_repository_capabilities_reject_invalid_artifacts(
    implementation: CapabilityImplementation,
    artifacts: tuple[Artifact, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        implementation.execute(request(implementation, *artifacts))

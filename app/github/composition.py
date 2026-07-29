"""Execution-scoped Capability assembly for the GitHub Runtime Host."""

from app.capabilities import CapabilityResolver, InMemoryCapabilityResolver
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
from app.github.client import GitHubClient
from app.github.repository import GitHubRepositoryReader
from app.github.workspace import RepositoryWorkspace
from app.host import HostEvent
from app.workflows import WorkflowDefinition


class GitHubCapabilityComposition:
    """Bind one GitHub event and workspace to provider-neutral implementations."""

    def __init__(
        self,
        *,
        repository: str,
        pull_request_number: int,
        installation_token: str,
        workspace: RepositoryWorkspace,
        ollama_model: str,
        github_api_url: str = "https://api.github.com",
        ollama_base_url: str = "http://localhost:11434",
    ) -> None:
        self._repository = repository
        self._pull_request_number = pull_request_number
        self._installation_token = installation_token
        self._workspace = workspace
        self._ollama_model = ollama_model
        self._github_api_url = github_api_url
        self._ollama_base_url = ollama_base_url

    def compose(
        self,
        event: HostEvent,
        workflow: WorkflowDefinition,
    ) -> CapabilityResolver:
        """Construct the resolver required by one already normalized execution."""
        if event.inputs.get("repository") != self._repository:
            raise ValueError("Host event repository does not match GitHub composition")
        if event.inputs.get("pull_request_number") != self._pull_request_number:
            raise ValueError(
                "Host event pull-request number does not match GitHub composition"
            )

        repository_reader = GitHubRepositoryReader(
            GitHubClient(
                self._installation_token,
                api_url=self._github_api_url,
            )
        )
        publisher = GitHubCommentPublisher(
            repository=self._repository,
            pull_request_number=self._pull_request_number,
            token=self._installation_token,
            api_url=self._github_api_url,
        )
        return InMemoryCapabilityResolver(
            (
                ReadChangedFilesImplementation(repository_reader),
                ReadFileImplementation(self._workspace.read_text),
                AnalyzeSourceCodeOllamaImplementation(
                    self._ollama_model,
                    base_url=self._ollama_base_url,
                ),
                MergeEngineeringFindingsImplementation(),
                GenerateMarkdownImplementation(),
                PublishGitHubCommentImplementation(publisher),
            )
        )

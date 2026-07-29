"""Provider-neutral implementation of the ReadPullRequest Capability."""

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)
from app.capabilities.repository import RepositoryReader

READ_PULL_REQUEST = Capability(
    name="ReadPullRequest",
    description="Read the metadata and current state of a repository pull request.",
    category=CapabilityCategory.REPOSITORY,
    contract="ReadPullRequest",
    version="1",
    input_artifacts=(
        ArtifactDefinition(name="repository", description="Repository identifier."),
        ArtifactDefinition(
            name="pull_request_number", description="Pull-request number."
        ),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="pull_request", description="Provider-neutral pull-request data."
        ),
    ),
    tags=("repository", "pull-request", "read"),
)


class ReadPullRequestImplementation:
    """Read pull-request data through an implementation-owned repository reader."""

    def __init__(self, repository_reader: RepositoryReader) -> None:
        self._repository_reader = repository_reader

    @property
    def capability(self) -> Capability:
        return READ_PULL_REQUEST

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        repository = request.artifact("repository").payload
        number = request.artifact("pull_request_number").payload
        if not isinstance(repository, str) or not repository:
            raise ValueError("repository artifact must contain a non-empty string")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ValueError("pull_request_number artifact must contain a positive integer")

        pull_request = self._repository_reader.read_pull_request(repository, number)
        return CapabilityResult(
            artifacts=(Artifact(name="pull_request", payload=pull_request),)
        )

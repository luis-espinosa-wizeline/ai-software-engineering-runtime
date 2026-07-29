"""Provider-neutral implementation of the ReadChangedFiles Capability."""

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)
from app.capabilities.repository import RepositoryReader

READ_CHANGED_FILES = Capability(
    name="ReadChangedFiles",
    description="Read the files changed by a repository pull request.",
    category=CapabilityCategory.REPOSITORY,
    contract="ReadChangedFiles",
    version="1",
    input_artifacts=(
        ArtifactDefinition(name="repository", description="Repository identifier."),
        ArtifactDefinition(
            name="pull_request_number", description="Pull-request number."
        ),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="changed_files", description="Provider-neutral changed-file data."
        ),
    ),
    tags=("repository", "pull-request", "files", "read"),
)


class ReadChangedFilesImplementation:
    """Read changed-file data through an implementation-owned repository reader."""

    def __init__(self, repository_reader: RepositoryReader) -> None:
        self._repository_reader = repository_reader

    @property
    def capability(self) -> Capability:
        return READ_CHANGED_FILES

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        repository = request.artifact("repository").payload
        number = request.artifact("pull_request_number").payload
        if not isinstance(repository, str) or not repository:
            raise ValueError("repository artifact must contain a non-empty string")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ValueError("pull_request_number artifact must contain a positive integer")

        files = self._repository_reader.read_changed_files(repository, number)
        return CapabilityResult(
            artifacts=(Artifact(name="changed_files", payload=files),)
        )

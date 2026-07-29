"""Engineering Delivery implementation for GitHub pull-request comments."""

from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)
from app.capabilities.documents import MarkdownDocument
from app.capabilities.publishing import EngineeringPublisher

PUBLISH_GITHUB_COMMENT = Capability(
    name="PublishGitHubComment",
    description="Publish a Markdown document as a GitHub Pull Request comment.",
    category=CapabilityCategory.PUBLISHING,
    contract="PublishGitHubComment",
    version="1",
    input_artifacts=(
        ArtifactDefinition(
            name="markdown", description="Final Markdown document to publish."
        ),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="publication_result",
            description="Provider-neutral publication outcome.",
        ),
    ),
    tags=("publishing", "github", "pull-request", "engineering-delivery"),
)


class PublishGitHubCommentImplementation:
    """Deliver a Markdown document through a configured publisher."""

    def __init__(self, publisher: EngineeringPublisher) -> None:
        self._publisher = publisher

    @property
    def capability(self) -> Capability:
        return PUBLISH_GITHUB_COMMENT

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        document = self._document(request.artifact("markdown"))
        publication = self._publisher.publish(document)
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="publication_result",
                    payload=publication.model_dump(mode="json"),
                ),
            )
        )

    @staticmethod
    def _document(artifact: Artifact) -> MarkdownDocument:
        try:
            return MarkdownDocument.model_validate(artifact.payload)
        except ValidationError as error:
            raise ValueError(
                "markdown artifact must contain a valid MarkdownDocument"
            ) from error

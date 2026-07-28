"""Mutable working memory for one execution plan run."""

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from app.capabilities.artifact import Artifact
from app.execution.errors import ArtifactAlreadyStored, ArtifactNotFound
from app.execution.plan import PlanIdentifier
from app.shared import JsonValue, RuntimeId


class ExecutionContext(BaseModel):
    """Mutable working memory belonging to one execution plan run."""

    model_config = ConfigDict(extra="forbid")

    execution_id: RuntimeId
    plan_id: PlanIdentifier
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    _step_artifacts: dict[str, dict[str, Artifact]] = PrivateAttr(default_factory=dict)

    def store_artifact(self, step_id: PlanIdentifier, artifact: Artifact) -> None:
        """Store one step output without allowing an existing artifact to be replaced."""
        artifacts = self._step_artifacts.setdefault(step_id, {})
        if artifact.name in artifacts:
            raise ArtifactAlreadyStored(step_id, artifact.name)
        artifacts[artifact.name] = artifact

    def get_artifact(
        self,
        step_id: PlanIdentifier,
        artifact_name: PlanIdentifier,
    ) -> Artifact:
        """Return a stored step artifact."""
        try:
            return self._step_artifacts[step_id][artifact_name]
        except KeyError as error:
            raise ArtifactNotFound(step_id, artifact_name) from error

    def has_artifact(
        self,
        step_id: PlanIdentifier,
        artifact_name: PlanIdentifier,
    ) -> bool:
        """Report whether a step artifact has been stored."""
        return artifact_name in self._step_artifacts.get(step_id, {})

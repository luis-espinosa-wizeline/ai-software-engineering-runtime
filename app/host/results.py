"""Provider-neutral outcome returned by a Runtime Host."""

from app.capabilities import Artifact
from app.shared import DomainModel, RuntimeId, WorkflowId


class HostExecutionResult(DomainModel):
    """Successful outcome of one workflow execution initiated by a Host."""

    execution_id: RuntimeId
    workflow_id: WorkflowId
    workflow_version: str
    success: bool
    final_artifact: Artifact

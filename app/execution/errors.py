"""Technology-agnostic errors raised by workflow lifecycle operations."""


class WorkflowLifecycleError(Exception):
    """Base error for workflow execution lifecycle violations."""


class InvalidWorkflowTransition(WorkflowLifecycleError):
    """Raised when a workflow execution cannot enter the requested state."""


class InvalidStepTransition(WorkflowLifecycleError):
    """Raised when a workflow step cannot enter the requested state."""


class UnknownWorkflowStep(WorkflowLifecycleError):
    """Raised when an execution does not contain the requested workflow step."""


class InvalidLifecycleTimestamp(WorkflowLifecycleError):
    """Raised when a lifecycle timestamp is naive or out of sequence."""


class InvalidWorkflowSteps(WorkflowLifecycleError):
    """Raised when execution steps do not match the workflow definition."""


class ExecutionContextError(Exception):
    """Base error for execution working-memory operations."""


class ArtifactAlreadyStored(ExecutionContextError):
    """Raised when an artifact would overwrite an existing step artifact."""

    def __init__(self, step_id: str, artifact_name: str) -> None:
        super().__init__(f"Artifact {artifact_name!r} is already stored for step {step_id!r}")


class ArtifactNotFound(ExecutionContextError):
    """Raised when a requested step artifact has not been stored."""

    def __init__(self, step_id: str, artifact_name: str) -> None:
        super().__init__(f"Artifact {artifact_name!r} was not found for step {step_id!r}")


class ExecutionEngineError(Exception):
    """Base error for deterministic execution engine failures."""


class ExecutionContextPlanMismatch(ExecutionEngineError):
    """Raised when a context belongs to a different execution plan."""

    def __init__(self, *, expected: str, actual: str) -> None:
        super().__init__(f"ExecutionContext belongs to plan {actual!r}; expected plan {expected!r}")


class MissingRequiredInput(ExecutionEngineError):
    """Raised when an execution context lacks an input required by the plan."""

    def __init__(self, input_name: str) -> None:
        super().__init__(f"Required execution input {input_name!r} is missing")


class MissingRequiredArtifact(ExecutionEngineError):
    """Raised when a step binding cannot resolve a required artifact."""

    def __init__(self, step_id: str, artifact_name: str) -> None:
        super().__init__(f"Required artifact {artifact_name!r} from step {step_id!r} is missing")


class WorkflowResultNotFound(ExecutionEngineError):
    """Raised when the plan's declared workflow result was not produced."""

    def __init__(self, step_id: str, artifact_name: str) -> None:
        super().__init__(
            f"Workflow result artifact {artifact_name!r} from step {step_id!r} is missing"
        )


class CapabilityContractMismatch(ExecutionEngineError):
    """Raised when capability resolution returns the wrong Action Contract."""

    def __init__(self, *, expected: str, actual: str) -> None:
        super().__init__(f"Resolved capability implements {actual!r}; expected {expected!r}")

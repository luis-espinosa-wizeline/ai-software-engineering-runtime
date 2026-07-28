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

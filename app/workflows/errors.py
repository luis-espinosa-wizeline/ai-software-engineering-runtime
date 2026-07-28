"""Technology-agnostic errors raised by workflow registry operations."""


class WorkflowRegistryError(Exception):
    """Base error for workflow discovery and registry failures."""


class DuplicateWorkflow(WorkflowRegistryError):
    """Raised when a workflow id and version occur more than once."""


class WorkflowNotFound(WorkflowRegistryError):
    """Raised when a requested workflow or version is not registered."""


class AmbiguousActiveWorkflow(WorkflowRegistryError):
    """Raised when a workflow id has more than one active version."""


class InvalidWorkflowDefinition(WorkflowRegistryError):
    """Raised when registry metadata on a workflow definition is invalid."""

"""Technology-agnostic errors raised by workflow services."""


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


class WorkflowInputValidationError(Exception):
    """Base error for structurally invalid Workflow invocation inputs."""


class MissingWorkflowInput(WorkflowInputValidationError):
    """Raised when a required Workflow input was not supplied."""

    def __init__(
        self,
        workflow_id: str,
        workflow_version: str,
        input_name: str,
        expected_type: str,
    ) -> None:
        super().__init__(
            f"Workflow {workflow_id!r} version {workflow_version!r} requires input "
            f"{input_name!r} of type {expected_type!r}; actual value is missing"
        )


class UnexpectedWorkflowInputs(WorkflowInputValidationError):
    """Raised when invocation inputs are not declared by the Workflow."""

    def __init__(
        self,
        workflow_id: str,
        workflow_version: str,
        input_names: tuple[str, ...],
    ) -> None:
        names = ", ".join(repr(name) for name in input_names)
        super().__init__(
            f"Workflow {workflow_id!r} version {workflow_version!r} received "
            f"unexpected input(s): {names}"
        )


class InvalidWorkflowInputType(WorkflowInputValidationError):
    """Raised when a Workflow input has the wrong structural type."""

    def __init__(
        self,
        workflow_id: str,
        workflow_version: str,
        input_name: str,
        expected_type: str,
        actual_type: str,
    ) -> None:
        super().__init__(
            f"Workflow {workflow_id!r} version {workflow_version!r} input "
            f"{input_name!r} expected type {expected_type!r}; "
            f"actual type is {actual_type!r}"
        )

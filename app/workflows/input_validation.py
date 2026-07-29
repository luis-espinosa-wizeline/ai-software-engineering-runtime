"""Strict structural validation of external Workflow inputs."""

from collections.abc import Mapping

from app.shared import JsonValue
from app.workflows.errors import (
    InvalidWorkflowInputType,
    MissingWorkflowInput,
    UnexpectedWorkflowInputs,
)
from app.workflows.models import (
    WorkflowDefinition,
    WorkflowInputType,
)


class WorkflowInputValidator:
    """Validate normalized inputs without coercion or provider knowledge."""

    def validate(
        self,
        workflow: WorkflowDefinition,
        inputs: Mapping[str, JsonValue],
    ) -> dict[str, JsonValue]:
        """Return a validated copy of inputs or raise a focused contract error."""
        unexpected = tuple(sorted(set(inputs) - set(workflow.input_names)))
        if unexpected:
            raise UnexpectedWorkflowInputs(
                workflow.workflow_id,
                workflow.version,
                unexpected,
            )

        for definition in workflow.inputs:
            if definition.name not in inputs:
                if definition.required:
                    raise MissingWorkflowInput(
                        workflow.workflow_id,
                        workflow.version,
                        definition.name,
                        definition.type.value,
                    )
                continue
            value = inputs[definition.name]
            if not self._matches(definition.type, value):
                raise InvalidWorkflowInputType(
                    workflow.workflow_id,
                    workflow.version,
                    definition.name,
                    definition.type.value,
                    self._actual_type(value),
                )

        return dict(inputs)

    @staticmethod
    def _matches(expected: WorkflowInputType, value: JsonValue) -> bool:
        match expected:
            case WorkflowInputType.STRING:
                return isinstance(value, str)
            case WorkflowInputType.INTEGER:
                return type(value) is int
            case WorkflowInputType.BOOLEAN:
                return type(value) is bool
            case WorkflowInputType.NUMBER:
                return type(value) in {int, float}
            case WorkflowInputType.OBJECT:
                return isinstance(value, dict)
            case WorkflowInputType.ARRAY:
                return isinstance(value, list)

    @staticmethod
    def _actual_type(value: JsonValue) -> str:
        if value is None:
            return "null"
        if type(value) is bool:
            return "boolean"
        if type(value) is int:
            return "integer"
        if type(value) is float:
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, dict):
            return "object"
        return "array"

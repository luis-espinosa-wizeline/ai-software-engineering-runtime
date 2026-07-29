"""Filesystem discovery and explicit parsing of declarative workflows."""

from collections.abc import Set
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.project.errors import DuplicateWorkflowName, InvalidWorkflowDefinitionFile
from app.project.yaml import load_yaml_mapping, require_exact_fields
from app.workflows.models import (
    WorkflowDefinition,
    WorkflowInputBinding,
    WorkflowInputDefinition,
    WorkflowInputReference,
    WorkflowInputType,
    WorkflowIteration,
    WorkflowResultReference,
    WorkflowStepDefinition,
    WorkflowStepOutputReference,
)


class WorkflowLoader:
    """Discover workflow YAML files and map them to the existing domain model."""

    def load(self, workflows_directory: str | Path) -> tuple[WorkflowDefinition, ...]:
        """Load direct .yaml children in deterministic workflow-name order."""
        directory = Path(workflows_directory)
        if not directory.is_dir():
            return ()

        discovered: list[tuple[WorkflowDefinition, Path]] = []
        by_name: dict[str, Path] = {}
        for path in sorted(directory.glob("*.yaml"), key=lambda item: item.name):
            workflow = self._load_file(path)
            previous = by_name.get(workflow.name)
            if previous is not None:
                raise DuplicateWorkflowName(workflow.name, previous, path)
            by_name[workflow.name] = path
            discovered.append((workflow, path))

        return tuple(
            workflow for workflow, _ in sorted(discovered, key=lambda item: item[0].name)
        )

    def _load_file(self, path: Path) -> WorkflowDefinition:
        data, parse_error = load_yaml_mapping(path)
        if parse_error is not None:
            raise InvalidWorkflowDefinitionFile(path, parse_error)
        assert data is not None
        try:
            return self._map_workflow(data)
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise InvalidWorkflowDefinitionFile(path, str(error)) from error

    def _map_workflow(self, data: dict[str, Any]) -> WorkflowDefinition:
        self._check_fields(
            data,
            required={"name", "inputs", "steps", "result"},
            optional={"description", "version"},
        )
        name = self._non_empty_string(data["name"], "name")
        version = self._non_empty_string(data.get("version", "1"), "version")
        description = self._optional_string(data.get("description"), "description")
        inputs = self._map_inputs(data["inputs"])
        steps = self._map_steps(data["steps"])
        result = self._map_result(data["result"])
        return WorkflowDefinition(
            workflow_id=name,
            name=name,
            version=version,
            description=description,
            inputs=inputs,
            steps=steps,
            result=result,
        )

    def _map_inputs(self, value: Any) -> tuple[WorkflowInputDefinition, ...]:
        mapping = self._mapping(value, "inputs")
        definitions: list[WorkflowInputDefinition] = []
        for name, definition in mapping.items():
            input_name = self._non_empty_string(name, "input name")
            input_definition = self._mapping(definition, f"input {input_name!r}")
            self._check_fields(
                input_definition,
                required={"type"},
                optional={"required"},
            )
            input_type = input_definition["type"]
            if not isinstance(input_type, str):
                raise TypeError(f"input {input_name!r} type must be a string")
            try:
                structural_type = WorkflowInputType(input_type)
            except ValueError as error:
                supported = ", ".join(item.value for item in WorkflowInputType)
                raise ValueError(
                    f"input {input_name!r} type {input_type!r} is unsupported; "
                    f"expected one of: {supported}"
                ) from error
            required = input_definition.get("required", True)
            if not isinstance(required, bool):
                raise TypeError(f"input {input_name!r} required must be a boolean")
            definitions.append(
                WorkflowInputDefinition(
                    name=input_name,
                    type=structural_type,
                    required=required,
                )
            )
        return tuple(definitions)

    def _map_steps(self, value: Any) -> tuple[WorkflowStepDefinition, ...]:
        if not isinstance(value, list):
            raise TypeError("steps must be a list")
        steps: list[WorkflowStepDefinition] = []
        for index, raw_step in enumerate(value):
            step = self._mapping(raw_step, f"steps[{index}]")
            self._check_fields(
                step,
                required={"id", "action", "inputs", "outputs"},
                optional={"name", "description", "iteration"},
            )
            step_id = self._non_empty_string(step["id"], f"steps[{index}].id")
            action = self._non_empty_string(step["action"], f"steps[{index}].action")
            outputs = self._string_list(step["outputs"], f"steps[{index}].outputs")
            bindings = self._map_bindings(step["inputs"], index)
            steps.append(
                WorkflowStepDefinition(
                    step_id=step_id,
                    name=self._non_empty_string(step.get("name", step_id), "step name"),
                    description=self._optional_string(
                        step.get("description"), "step description"
                    ),
                    action_contract=action,
                    input_bindings=bindings,
                    outputs=outputs,
                    iteration=self._map_iteration(step.get("iteration"), index),
                )
            )
        return tuple(steps)

    def _map_bindings(
        self, value: Any, step_index: int
    ) -> tuple[WorkflowInputBinding, ...]:
        mapping = self._mapping(value, f"steps[{step_index}].inputs")
        bindings: list[WorkflowInputBinding] = []
        for parameter, raw_source in mapping.items():
            parameter_name = self._non_empty_string(parameter, "input parameter")
            source = self._mapping(raw_source, f"binding {parameter_name!r}")
            reference: WorkflowInputReference | WorkflowStepOutputReference
            if set(source) == {"workflow_input"}:
                reference = WorkflowInputReference(
                    input_name=self._non_empty_string(
                        source["workflow_input"], "workflow_input"
                    )
                )
            elif set(source) == {"step_output"}:
                output = self._mapping(source["step_output"], "step_output")
                self._check_fields(output, required={"step", "artifact"})
                reference = WorkflowStepOutputReference(
                    step_id=self._non_empty_string(output["step"], "step_output.step"),
                    output_name=self._non_empty_string(
                        output["artifact"], "step_output.artifact"
                    ),
                )
            else:
                raise ValueError(
                    f"binding {parameter_name!r} must contain exactly one of "
                    "workflow_input or step_output"
                )
            bindings.append(
                WorkflowInputBinding(parameter=parameter_name, source=reference)
            )
        return tuple(bindings)

    def _map_iteration(
        self, value: Any, step_index: int
    ) -> WorkflowIteration | None:
        if value is None:
            return None
        iteration = self._mapping(value, f"steps[{step_index}].iteration")
        self._check_fields(iteration, required={"input"})
        return WorkflowIteration(
            input_parameter=self._non_empty_string(
                iteration["input"], f"steps[{step_index}].iteration.input"
            )
        )

    def _map_result(self, value: Any) -> WorkflowResultReference:
        result = self._mapping(value, "result")
        self._check_fields(result, required={"step", "artifact"})
        return WorkflowResultReference(
            step_id=self._non_empty_string(result["step"], "result.step"),
            output_name=self._non_empty_string(result["artifact"], "result.artifact"),
        )

    @staticmethod
    def _mapping(value: Any, field: str) -> dict[str, Any]:
        if not isinstance(value, dict) or not all(
            isinstance(key, str) for key in value
        ):
            raise TypeError(f"{field} must be a mapping with string field names")
        return value

    @staticmethod
    def _check_fields(
        data: dict[str, Any],
        *,
        required: Set[str],
        optional: Set[str] = frozenset(),
    ) -> None:
        error = require_exact_fields(data, required=required, optional=optional)
        if error is not None:
            raise ValueError(error)

    @staticmethod
    def _non_empty_string(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise TypeError(f"{field} must be a non-empty string")
        return value

    @staticmethod
    def _optional_string(value: Any, field: str) -> str | None:
        if value is None:
            return None
        return WorkflowLoader._non_empty_string(value, field)

    @staticmethod
    def _string_list(value: Any, field: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise TypeError(f"{field} must be a list")
        return tuple(
            WorkflowLoader._non_empty_string(item, f"{field} item") for item in value
        )

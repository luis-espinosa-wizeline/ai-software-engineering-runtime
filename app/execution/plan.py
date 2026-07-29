"""Provider-neutral execution strategy domain models."""

from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.shared import DomainModel, WorkflowId

type PlanIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]


class PlanInputReference(DomainModel):
    """A reference to an input required by an execution plan."""

    input_name: PlanIdentifier


class StepOutputReference(DomainModel):
    """A reference to an output produced by an earlier plan step."""

    step_id: PlanIdentifier
    output_name: PlanIdentifier


type InputReference = PlanInputReference | StepOutputReference


class InputBinding(DomainModel):
    """Binds a step parameter to a value declared elsewhere in the plan."""

    parameter: PlanIdentifier
    source: InputReference


class Iteration(DomainModel):
    """Expand one bound collection into ordered Capability invocations."""

    input_parameter: PlanIdentifier


class ExecutionPlanStep(DomainModel):
    """One provider-neutral action required by an execution strategy."""

    step_id: PlanIdentifier
    action_contract: PlanIdentifier
    input_bindings: tuple[InputBinding, ...] = ()
    outputs: tuple[PlanIdentifier, ...] = ()
    iteration: Iteration | None = None

    @model_validator(mode="after")
    def validate_unique_outputs(self) -> ExecutionPlanStep:
        """Ensure every output can be referenced unambiguously."""
        if len(self.outputs) != len(set(self.outputs)):
            raise ValueError(f"Step {self.step_id!r} contains duplicate output names")
        if self.iteration is not None:
            parameters = tuple(binding.parameter for binding in self.input_bindings)
            if parameters.count(self.iteration.input_parameter) != 1:
                raise ValueError(
                    f"Step {self.step_id!r} iteration must reference exactly one bound input "
                    f"{self.iteration.input_parameter!r}"
                )
            if not self.outputs:
                raise ValueError(
                    f"Iterated step {self.step_id!r} must declare output names"
                )
        return self


class PlanResultReference(DomainModel):
    """The step output that becomes the final result of an execution plan."""

    step_id: PlanIdentifier
    output_name: PlanIdentifier


class ExecutionPlan(DomainModel):
    """An immutable, reusable strategy for executing a workflow."""

    plan_id: PlanIdentifier
    workflow_id: WorkflowId = Field(min_length=1)
    workflow_version: str = Field(min_length=1)
    required_inputs: tuple[PlanIdentifier, ...] = ()
    steps: tuple[ExecutionPlanStep, ...] = Field(min_length=1)
    result: PlanResultReference

    @model_validator(mode="after")
    def validate_references(self) -> ExecutionPlan:
        """Validate plan structure and all input and result references."""
        self._validate_unique_required_inputs()
        step_positions = self._step_positions()
        self._validate_bindings(step_positions)
        self._validate_result(step_positions)
        return self

    def _validate_unique_required_inputs(self) -> None:
        if len(self.required_inputs) != len(set(self.required_inputs)):
            raise ValueError("Execution plan contains duplicate required input names")

    def _step_positions(self) -> dict[str, int]:
        positions: dict[str, int] = {}
        for position, step in enumerate(self.steps):
            if step.step_id in positions:
                raise ValueError(f"Execution plan contains duplicate step id {step.step_id!r}")
            positions[step.step_id] = position
        return positions

    def _validate_bindings(self, step_positions: dict[str, int]) -> None:
        required_inputs = set(self.required_inputs)
        outputs_by_step = {step.step_id: set(step.outputs) for step in self.steps}

        for position, step in enumerate(self.steps):
            for binding in step.input_bindings:
                source = binding.source
                if isinstance(source, PlanInputReference):
                    if source.input_name not in required_inputs:
                        raise ValueError(
                            f"Step {step.step_id!r} binding {binding.parameter!r} references "
                            f"unknown plan input {source.input_name!r}"
                        )
                    continue

                referenced_position = step_positions.get(source.step_id)
                if referenced_position is None:
                    raise ValueError(
                        f"Step {step.step_id!r} binding {binding.parameter!r} references "
                        f"unknown step {source.step_id!r}"
                    )
                if referenced_position == position:
                    raise ValueError(f"Step {step.step_id!r} cannot reference itself")
                if referenced_position > position:
                    raise ValueError(
                        f"Step {step.step_id!r} cannot reference future step {source.step_id!r}"
                    )
                if source.output_name not in outputs_by_step[source.step_id]:
                    raise ValueError(
                        f"Step {step.step_id!r} references unknown output "
                        f"{source.output_name!r} from step {source.step_id!r}"
                    )

    def _validate_result(self, step_positions: dict[str, int]) -> None:
        if self.result.step_id not in step_positions:
            raise ValueError(
                f"Plan result references unknown step {self.result.step_id!r}"
            )

        result_step = self.steps[step_positions[self.result.step_id]]
        if self.result.output_name not in result_step.outputs:
            raise ValueError(
                f"Plan result references unknown output {self.result.output_name!r} "
                f"from step {self.result.step_id!r}"
            )

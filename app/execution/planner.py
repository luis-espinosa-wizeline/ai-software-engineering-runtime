"""Deterministic transformation of workflow intent into execution strategy."""

from pydantic import ValidationError

from app.execution.plan import (
    ExecutionPlan,
    ExecutionPlanStep,
    InputBinding,
    Iteration,
    PlanInputReference,
    PlanResultReference,
    StepOutputReference,
)
from app.workflows import (
    WorkflowDefinition,
    WorkflowInputBinding,
    WorkflowInputReference,
    WorkflowStepDefinition,
    WorkflowStepOutputReference,
)


class ExecutionPlannerError(Exception):
    """Base error for deterministic execution planning failures."""


class InvalidWorkflowForPlanning(ExecutionPlannerError):
    """Raised when a workflow lacks a valid declarative planning structure."""


class WorkflowSemanticError(ExecutionPlannerError):
    """Raised when workflow references or dependencies are semantically invalid."""


class ExecutionPlanConstructionError(ExecutionPlannerError):
    """Raised when validated workflow intent cannot construct an execution plan."""


class ExecutionPlanner:
    """Validate workflow intent and compile it into an immutable execution plan."""

    def plan(self, workflow: WorkflowDefinition) -> ExecutionPlan:
        """Produce the deterministic execution plan for a workflow definition."""
        self._validate_definition(workflow)
        self._validate_semantics(workflow)
        result = workflow.result
        assert result is not None

        try:
            return ExecutionPlan(
                plan_id=f"{workflow.workflow_id}.{workflow.version}",
                workflow_id=workflow.workflow_id,
                workflow_version=workflow.version,
                required_inputs=workflow.required_inputs,
                steps=tuple(self._build_step(step) for step in workflow.steps),
                result=PlanResultReference(
                    step_id=result.step_id,
                    output_name=result.output_name,
                ),
            )
        except ValidationError as error:
            raise ExecutionPlanConstructionError(
                f"Workflow {workflow.workflow_id!r} could not produce a valid execution plan"
            ) from error

    @staticmethod
    def _validate_definition(workflow: WorkflowDefinition) -> None:
        if not workflow.workflow_id:
            raise InvalidWorkflowForPlanning("Workflow id is required for planning")
        if not workflow.version:
            raise InvalidWorkflowForPlanning("Workflow version is required for planning")
        if not workflow.steps:
            raise InvalidWorkflowForPlanning("Workflow must declare at least one step")
        if workflow.result is None:
            raise InvalidWorkflowForPlanning("Workflow must declare a result reference")

        step_ids = tuple(step.step_id for step in workflow.steps)
        if len(step_ids) != len(set(step_ids)):
            raise InvalidWorkflowForPlanning("Workflow contains duplicate step identifiers")
        if len(workflow.required_inputs) != len(set(workflow.required_inputs)):
            raise InvalidWorkflowForPlanning("Workflow contains duplicate required inputs")

        optional_inputs = set(workflow.input_names) - set(workflow.required_inputs)
        for step in workflow.steps:
            if step.action_contract is None:
                raise InvalidWorkflowForPlanning(
                    f"Workflow step {step.step_id!r} must declare an action contract"
                )
            if len(step.outputs) != len(set(step.outputs)):
                raise InvalidWorkflowForPlanning(
                    f"Workflow step {step.step_id!r} contains duplicate outputs"
                )
            parameters = tuple(binding.parameter for binding in step.input_bindings)
            if len(parameters) != len(set(parameters)):
                raise InvalidWorkflowForPlanning(
                    f"Workflow step {step.step_id!r} contains duplicate input parameters"
                )
            for binding in step.input_bindings:
                source = binding.source
                if (
                    isinstance(source, WorkflowInputReference)
                    and source.input_name in optional_inputs
                ):
                    raise InvalidWorkflowForPlanning(
                        f"Workflow step {step.step_id!r} binds optional workflow input "
                        f"{source.input_name!r}; optional bindings require an explicit "
                        "default or conditional execution semantic"
                    )
            if step.iteration is not None:
                if step.iteration.input_parameter not in parameters:
                    raise InvalidWorkflowForPlanning(
                        f"Workflow step {step.step_id!r} iteration references unbound "
                        f"input {step.iteration.input_parameter!r}"
                    )
                if not step.outputs:
                    raise InvalidWorkflowForPlanning(
                        f"Iterated workflow step {step.step_id!r} must declare outputs"
                    )

    def _validate_semantics(self, workflow: WorkflowDefinition) -> None:
        positions = {step.step_id: position for position, step in enumerate(workflow.steps)}
        outputs = {step.step_id: set(step.outputs) for step in workflow.steps}
        dependencies = self._dependencies(workflow, positions, outputs)

        self._validate_acyclic(dependencies)
        self._validate_order(workflow, positions)
        self._validate_result(workflow, positions, outputs)
        self._validate_reachability(workflow, dependencies)

    @staticmethod
    def _dependencies(
        workflow: WorkflowDefinition,
        positions: dict[str, int],
        outputs: dict[str, set[str]],
    ) -> dict[str, set[str]]:
        dependencies = {step.step_id: set[str]() for step in workflow.steps}
        declared_inputs = set(workflow.input_names)

        for step in workflow.steps:
            for binding in step.input_bindings:
                source = binding.source
                if isinstance(source, WorkflowInputReference):
                    if source.input_name not in declared_inputs:
                        raise WorkflowSemanticError(
                            f"Step {step.step_id!r} references unknown workflow input "
                            f"{source.input_name!r}"
                        )
                    continue

                if source.step_id not in positions:
                    raise WorkflowSemanticError(
                        f"Step {step.step_id!r} references unknown step {source.step_id!r}"
                    )
                if source.output_name not in outputs[source.step_id]:
                    raise WorkflowSemanticError(
                        f"Step {step.step_id!r} references unknown output "
                        f"{source.output_name!r} from step {source.step_id!r}"
                    )
                dependencies[step.step_id].add(source.step_id)

        return dependencies

    @staticmethod
    def _validate_acyclic(dependencies: dict[str, set[str]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise WorkflowSemanticError("Workflow contains cyclic step dependencies")
            if step_id in visited:
                return

            visiting.add(step_id)
            for dependency in dependencies[step_id]:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in dependencies:
            visit(step_id)

    @staticmethod
    def _validate_order(
        workflow: WorkflowDefinition,
        positions: dict[str, int],
    ) -> None:
        for position, step in enumerate(workflow.steps):
            for binding in step.input_bindings:
                source = binding.source
                if not isinstance(source, WorkflowStepOutputReference):
                    continue
                referenced_position = positions[source.step_id]
                if referenced_position == position:
                    raise WorkflowSemanticError(
                        f"Step {step.step_id!r} cannot reference itself"
                    )
                if referenced_position > position:
                    raise WorkflowSemanticError(
                        f"Step {step.step_id!r} cannot reference future step "
                        f"{source.step_id!r}"
                    )

    @staticmethod
    def _validate_result(
        workflow: WorkflowDefinition,
        positions: dict[str, int],
        outputs: dict[str, set[str]],
    ) -> None:
        assert workflow.result is not None
        if workflow.result.step_id not in positions:
            raise WorkflowSemanticError(
                f"Workflow result references unknown step {workflow.result.step_id!r}"
            )
        if workflow.result.output_name not in outputs[workflow.result.step_id]:
            raise WorkflowSemanticError(
                f"Workflow result references unknown output {workflow.result.output_name!r} "
                f"from step {workflow.result.step_id!r}"
            )

    @staticmethod
    def _validate_reachability(
        workflow: WorkflowDefinition,
        dependencies: dict[str, set[str]],
    ) -> None:
        assert workflow.result is not None
        reachable: set[str] = set()
        pending = [workflow.result.step_id]

        while pending:
            step_id = pending.pop()
            if step_id in reachable:
                continue
            reachable.add(step_id)
            pending.extend(dependencies[step_id])

        unreachable = tuple(
            step.step_id for step in workflow.steps if step.step_id not in reachable
        )
        if unreachable:
            identifiers = ", ".join(unreachable)
            raise WorkflowSemanticError(
                f"Workflow contains steps that do not contribute to its result: {identifiers}"
            )

    @staticmethod
    def _build_step(step: WorkflowStepDefinition) -> ExecutionPlanStep:
        assert step.action_contract is not None
        return ExecutionPlanStep(
            step_id=step.step_id,
            action_contract=step.action_contract,
            input_bindings=tuple(
                ExecutionPlanner._build_binding(binding)
                for binding in step.input_bindings
            ),
            outputs=step.outputs,
            iteration=(
                Iteration(input_parameter=step.iteration.input_parameter)
                if step.iteration is not None
                else None
            ),
        )

    @staticmethod
    def _build_binding(binding: WorkflowInputBinding) -> InputBinding:
        source = binding.source
        plan_source: PlanInputReference | StepOutputReference
        if isinstance(source, WorkflowInputReference):
            plan_source = PlanInputReference(input_name=source.input_name)
        else:
            plan_source = StepOutputReference(
                step_id=source.step_id,
                output_name=source.output_name,
            )
        return InputBinding(parameter=binding.parameter, source=plan_source)

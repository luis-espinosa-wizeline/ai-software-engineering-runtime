"""Deterministic sequential execution of immutable execution plans."""

from app.capabilities import (
    Artifact,
    CapabilityImplementation,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
)
from app.execution.context import ExecutionContext
from app.execution.errors import (
    ArtifactNotFound,
    CapabilityContractMismatch,
    ExecutionContextPlanMismatch,
    IterationInputNotCollection,
    IterationOutputMismatch,
    MissingRequiredArtifact,
    MissingRequiredInput,
    WorkflowResultNotFound,
)
from app.execution.plan import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanInputReference,
    StepOutputReference,
)
from app.shared import JsonValue


class ExecutionEngine:
    """Execute plan steps sequentially without making workflow decisions."""

    def __init__(self, capability_resolver: CapabilityResolver) -> None:
        self._capability_resolver = capability_resolver

    def execute(self, plan: ExecutionPlan, context: ExecutionContext) -> Artifact:
        """Execute every plan step and return its declaratively selected result."""
        self._validate_context(plan, context)
        self._validate_required_inputs(plan, context)

        for step in plan.steps:
            self._execute_step(step, context)

        return self._resolve_workflow_result(plan, context)

    def _execute_step(
        self,
        step: ExecutionPlanStep,
        context: ExecutionContext,
    ) -> None:
        implementation = self._capability_resolver.resolve(step.action_contract)
        if implementation.capability.contract != step.action_contract:
            raise CapabilityContractMismatch(
                expected=step.action_contract,
                actual=implementation.capability.contract,
            )

        artifacts = tuple(
            self._resolve_binding(binding.parameter, binding.source, context)
            for binding in step.input_bindings
        )
        if step.iteration is not None:
            self._execute_iteration(step, artifacts, implementation, context)
            return

        result = self._invoke(implementation, artifacts)
        for artifact in result.artifacts:
            context.store_artifact(step.step_id, artifact)

    @staticmethod
    def _invoke(
        implementation: CapabilityImplementation,
        artifacts: tuple[Artifact, ...],
    ) -> CapabilityResult:
        return implementation.execute(
            CapabilityRequest(
                capability=implementation.capability,
                artifacts=artifacts,
            )
        )

    def _execute_iteration(
        self,
        step: ExecutionPlanStep,
        artifacts: tuple[Artifact, ...],
        implementation: CapabilityImplementation,
        context: ExecutionContext,
    ) -> None:
        assert step.iteration is not None
        parameter = step.iteration.input_parameter
        iterated_artifact = next(
            artifact for artifact in artifacts if artifact.name == parameter
        )
        collection = iterated_artifact.payload
        if not isinstance(collection, list):
            raise IterationInputNotCollection(step.step_id, parameter)

        collected: dict[str, list[JsonValue]] = {
            output: [] for output in step.outputs
        }
        for index, item in enumerate(collection):
            invocation_artifacts = tuple(
                Artifact(name=artifact.name, payload=item)
                if artifact.name == parameter
                else artifact
                for artifact in artifacts
            )
            result = self._invoke(implementation, invocation_artifacts)
            self._collect_iteration_result(step, index, result, collected)

        for output_name, payloads in collected.items():
            context.store_artifact(
                step.step_id,
                Artifact(name=output_name, payload=payloads),
            )

    @staticmethod
    def _collect_iteration_result(
        step: ExecutionPlanStep,
        index: int,
        result: CapabilityResult,
        collected: dict[str, list[JsonValue]],
    ) -> None:
        actual = tuple(artifact.name for artifact in result.artifacts)
        if len(actual) != len(set(actual)) or set(actual) != set(step.outputs):
            raise IterationOutputMismatch(
                step.step_id,
                index,
                expected=step.outputs,
                actual=actual,
            )
        by_name = {artifact.name: artifact for artifact in result.artifacts}
        for output in step.outputs:
            collected[output].append(by_name[output].payload)

    @staticmethod
    def _resolve_binding(
        parameter: str,
        source: PlanInputReference | StepOutputReference,
        context: ExecutionContext,
    ) -> Artifact:
        if isinstance(source, PlanInputReference):
            try:
                return Artifact(name=parameter, payload=context.inputs[source.input_name])
            except KeyError as error:
                raise MissingRequiredInput(source.input_name) from error

        try:
            source_artifact = context.get_artifact(source.step_id, source.output_name)
            return Artifact(
                name=parameter,
                payload=source_artifact.payload,
                metadata=source_artifact.metadata,
            )
        except ArtifactNotFound as error:
            raise MissingRequiredArtifact(source.step_id, source.output_name) from error

    @staticmethod
    def _validate_context(plan: ExecutionPlan, context: ExecutionContext) -> None:
        if context.plan_id != plan.plan_id:
            raise ExecutionContextPlanMismatch(
                expected=plan.plan_id,
                actual=context.plan_id,
            )

    @staticmethod
    def _validate_required_inputs(
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> None:
        for input_name in plan.required_inputs:
            if input_name not in context.inputs:
                raise MissingRequiredInput(input_name)

    @staticmethod
    def _resolve_workflow_result(
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> Artifact:
        try:
            return context.get_artifact(
                plan.result.step_id,
                plan.result.output_name,
            )
        except ArtifactNotFound as error:
            raise WorkflowResultNotFound(
                plan.result.step_id,
                plan.result.output_name,
            ) from error

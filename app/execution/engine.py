"""Deterministic sequential execution of immutable execution plans."""

from app.capabilities import Artifact, CapabilityRequest, CapabilityResolver
from app.execution.context import ExecutionContext
from app.execution.errors import (
    ArtifactNotFound,
    CapabilityContractMismatch,
    ExecutionContextPlanMismatch,
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
        request = CapabilityRequest(
            action_contract=step.action_contract,
            inputs={
                binding.parameter: self._resolve_binding(binding.source, context)
                for binding in step.input_bindings
            },
        )
        capability = self._capability_resolver.resolve(step.action_contract)
        if capability.action_contract != step.action_contract:
            raise CapabilityContractMismatch(
                expected=step.action_contract,
                actual=capability.action_contract,
            )

        result = capability.execute(request)
        for artifact in result.artifacts:
            context.store_artifact(step.step_id, artifact)

    @staticmethod
    def _resolve_binding(
        source: PlanInputReference | StepOutputReference,
        context: ExecutionContext,
    ) -> JsonValue:
        if isinstance(source, PlanInputReference):
            try:
                return context.inputs[source.input_name]
            except KeyError as error:
                raise MissingRequiredInput(source.input_name) from error

        try:
            return context.get_artifact(source.step_id, source.output_name).payload
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

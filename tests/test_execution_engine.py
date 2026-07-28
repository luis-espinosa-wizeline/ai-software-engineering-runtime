from collections.abc import Callable
from uuid import UUID

import pytest

from app.capabilities import (
    Artifact,
    CapabilityRequest,
    CapabilityResult,
    InMemoryCapabilityResolver,
    MissingCapability,
)
from app.execution import (
    ExecutionContext,
    ExecutionContextPlanMismatch,
    ExecutionEngine,
    ExecutionPlan,
    ExecutionPlanStep,
    InputBinding,
    MissingRequiredArtifact,
    MissingRequiredInput,
    PlanInputReference,
    PlanResultReference,
    StepOutputReference,
    WorkflowResultNotFound,
)
from app.shared import JsonValue

EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000001")


class RecordingCapability:
    def __init__(
        self,
        action_contract: str,
        implementation: Callable[[CapabilityRequest], CapabilityResult],
    ) -> None:
        self._action_contract = action_contract
        self._implementation = implementation
        self.requests: list[CapabilityRequest] = []

    @property
    def action_contract(self) -> str:
        return self._action_contract

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self.requests.append(request)
        return self._implementation(request)


def context_for(
    plan: ExecutionPlan,
    *,
    inputs: dict[str, JsonValue] | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        execution_id=EXECUTION_ID,
        plan_id=plan.plan_id,
        inputs=inputs or {},
    )


def multi_step_plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="pull-request-review.1",
        workflow_id="pull-request-review",
        workflow_version="1",
        required_inputs=("repository", "pull_request"),
        steps=(
            ExecutionPlanStep(
                step_id="retrieve-changes",
                action_contract="repository.retrieve_changes",
                input_bindings=(
                    InputBinding(
                        parameter="repository",
                        source=PlanInputReference(input_name="repository"),
                    ),
                    InputBinding(
                        parameter="pull_request",
                        source=PlanInputReference(input_name="pull_request"),
                    ),
                ),
                outputs=("changes",),
            ),
            ExecutionPlanStep(
                step_id="analyze-code",
                action_contract="code.analysis",
                input_bindings=(
                    InputBinding(
                        parameter="changes",
                        source=StepOutputReference(
                            step_id="retrieve-changes",
                            output_name="changes",
                        ),
                    ),
                ),
                outputs=("review",),
            ),
        ),
        result=PlanResultReference(
            step_id="analyze-code",
            output_name="review",
        ),
    )


def test_engine_executes_multiple_steps_sequentially_and_resolves_bindings() -> None:
    execution_order: list[str] = []

    def retrieve_changes(request: CapabilityRequest) -> CapabilityResult:
        execution_order.append("retrieve")
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="changes",
                    payload={
                        "repository": request.inputs["repository"],
                        "pull_request": request.inputs["pull_request"],
                    },
                ),
            )
        )

    def analyze_code(request: CapabilityRequest) -> CapabilityResult:
        execution_order.append("analyze")
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="review",
                    payload={"changes": request.inputs["changes"], "approved": True},
                ),
            )
        )

    retrieve = RecordingCapability(
        "repository.retrieve_changes",
        retrieve_changes,
    )
    analyze = RecordingCapability(
        "code.analysis",
        analyze_code,
    )
    plan = multi_step_plan()
    context = context_for(
        plan,
        inputs={"repository": "example/runtime", "pull_request": 42},
    )
    engine = ExecutionEngine(InMemoryCapabilityResolver((analyze, retrieve)))

    result = engine.execute(plan, context)

    assert execution_order == ["retrieve", "analyze"]
    assert retrieve.requests == [
        CapabilityRequest(
            action_contract="repository.retrieve_changes",
            inputs={"repository": "example/runtime", "pull_request": 42},
        )
    ]
    assert analyze.requests == [
        CapabilityRequest(
            action_contract="code.analysis",
            inputs={
                "changes": {
                    "repository": "example/runtime",
                    "pull_request": 42,
                }
            },
        )
    ]
    assert context.get_artifact("retrieve-changes", "changes").payload == {
        "repository": "example/runtime",
        "pull_request": 42,
    }
    assert context.get_artifact("analyze-code", "review") is result


def test_engine_executes_single_step_and_returns_declared_result() -> None:
    plan = ExecutionPlan(
        plan_id="summarize.1",
        workflow_id="summarize",
        workflow_version="1",
        required_inputs=("text",),
        steps=(
            ExecutionPlanStep(
                step_id="summarize",
                action_contract="text.summarize",
                input_bindings=(
                    InputBinding(
                        parameter="text",
                        source=PlanInputReference(input_name="text"),
                    ),
                ),
                outputs=("summary", "diagnostic"),
            ),
        ),
        result=PlanResultReference(step_id="summarize", output_name="summary"),
    )
    summary = Artifact(name="summary", payload="Short")
    diagnostic = Artifact(name="diagnostic", payload="Not the workflow result")
    capability = RecordingCapability(
        "text.summarize",
        lambda request: CapabilityResult(artifacts=(summary, diagnostic)),
    )
    context = context_for(plan, inputs={"text": "Long text"})

    result = ExecutionEngine(InMemoryCapabilityResolver((capability,))).execute(plan, context)

    assert result is summary
    assert result is not diagnostic
    assert context.get_artifact("summarize", "diagnostic") is diagnostic


def test_engine_owns_context_mutation_and_stores_result_after_invocation() -> None:
    plan = ExecutionPlan(
        plan_id="produce.1",
        workflow_id="produce",
        workflow_version="1",
        steps=(
            ExecutionPlanStep(
                step_id="produce",
                action_contract="artifact.produce",
                outputs=("result",),
            ),
        ),
        result=PlanResultReference(step_id="produce", output_name="result"),
    )
    context = context_for(plan)
    observed_before_return: list[bool] = []

    def produce(request: CapabilityRequest) -> CapabilityResult:
        assert request == CapabilityRequest(action_contract="artifact.produce")
        observed_before_return.append(context.has_artifact("produce", "result"))
        return CapabilityResult(artifacts=(Artifact(name="result", payload="done"),))

    result = ExecutionEngine(
        InMemoryCapabilityResolver((RecordingCapability("artifact.produce", produce),))
    ).execute(plan, context)

    assert observed_before_return == [False]
    assert context.get_artifact("produce", "result") is result


def test_engine_rejects_missing_capability() -> None:
    plan = multi_step_plan()
    context = context_for(
        plan,
        inputs={"repository": "example/runtime", "pull_request": 42},
    )

    with pytest.raises(MissingCapability, match="repository.retrieve_changes"):
        ExecutionEngine(InMemoryCapabilityResolver(())).execute(plan, context)


def test_engine_rejects_missing_required_input_before_execution() -> None:
    plan = multi_step_plan()
    context = context_for(plan, inputs={"repository": "example/runtime"})
    capability = RecordingCapability(
        "repository.retrieve_changes",
        lambda request: CapabilityResult(artifacts=(Artifact(name="changes", payload="diff"),)),
    )

    with pytest.raises(MissingRequiredInput, match="pull_request"):
        ExecutionEngine(InMemoryCapabilityResolver((capability,))).execute(plan, context)

    assert capability.requests == []


def test_engine_rejects_missing_artifact_binding() -> None:
    plan = multi_step_plan()
    retrieve = RecordingCapability(
        "repository.retrieve_changes",
        lambda request: CapabilityResult(artifacts=(Artifact(name="unexpected", payload="diff"),)),
    )
    analyze = RecordingCapability(
        "code.analysis",
        lambda request: CapabilityResult(artifacts=(Artifact(name="review", payload="approved"),)),
    )
    context = context_for(
        plan,
        inputs={"repository": "example/runtime", "pull_request": 42},
    )

    with pytest.raises(MissingRequiredArtifact, match="changes.*retrieve-changes"):
        ExecutionEngine(InMemoryCapabilityResolver((retrieve, analyze))).execute(plan, context)

    assert len(retrieve.requests) == 1
    assert analyze.requests == []


def test_engine_rejects_missing_declared_workflow_result() -> None:
    plan = ExecutionPlan(
        plan_id="review.1",
        workflow_id="review",
        workflow_version="1",
        steps=(
            ExecutionPlanStep(
                step_id="review",
                action_contract="code.review",
                outputs=("review",),
            ),
        ),
        result=PlanResultReference(step_id="review", output_name="review"),
    )
    capability = RecordingCapability(
        "code.review",
        lambda request: CapabilityResult(
            artifacts=(Artifact(name="unexpected", payload="approved"),)
        ),
    )

    with pytest.raises(WorkflowResultNotFound, match="review"):
        ExecutionEngine(InMemoryCapabilityResolver((capability,))).execute(plan, context_for(plan))


def test_engine_rejects_context_for_another_plan() -> None:
    plan = multi_step_plan()
    context = ExecutionContext(
        execution_id=EXECUTION_ID,
        plan_id="different-plan.1",
        inputs={"repository": "example/runtime", "pull_request": 42},
    )

    with pytest.raises(ExecutionContextPlanMismatch, match="different-plan"):
        ExecutionEngine(InMemoryCapabilityResolver(())).execute(plan, context)

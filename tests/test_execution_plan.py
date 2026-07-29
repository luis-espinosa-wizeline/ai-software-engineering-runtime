import pytest
from pydantic import ValidationError

from app.execution import (
    ExecutionPlan,
    ExecutionPlanStep,
    InputBinding,
    Iteration,
    PlanInputReference,
    PlanResultReference,
    StepOutputReference,
)


def valid_plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="pull-request-review.v1",
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
        result=PlanResultReference(step_id="analyze-code", output_name="review"),
    )


def test_valid_plan_describes_a_reusable_execution_strategy() -> None:
    plan = valid_plan()

    assert plan.plan_id == "pull-request-review.v1"
    assert plan.required_inputs == ("repository", "pull_request")
    assert tuple(step.step_id for step in plan.steps) == (
        "retrieve-changes",
        "analyze-code",
    )
    assert plan.result == PlanResultReference(
        step_id="analyze-code",
        output_name="review",
    )


def test_plan_requires_an_identifier_and_at_least_one_step() -> None:
    with pytest.raises(ValidationError):
        ExecutionPlan(
            plan_id="",
            workflow_id="review",
            workflow_version="1",
            steps=(
                ExecutionPlanStep(
                    step_id="review",
                    action_contract="code.analysis",
                    outputs=("review",),
                ),
            ),
            result=PlanResultReference(step_id="review", output_name="review"),
        )

    with pytest.raises(ValidationError):
        ExecutionPlan(
            plan_id="review",
            workflow_id="review",
            workflow_version="1",
            steps=(),
            result=PlanResultReference(step_id="review", output_name="review"),
        )


def test_plan_rejects_duplicate_step_ids() -> None:
    duplicate = ExecutionPlanStep(
        step_id="analyze",
        action_contract="code.analysis",
        outputs=("review",),
    )

    with pytest.raises(ValidationError, match="duplicate step id"):
        ExecutionPlan(
            plan_id="review",
            workflow_id="review",
            workflow_version="1",
            steps=(duplicate, duplicate),
            result=PlanResultReference(step_id="analyze", output_name="review"),
        )


def test_step_requires_an_action_contract_and_unique_outputs() -> None:
    with pytest.raises(ValidationError):
        ExecutionPlanStep(step_id="analyze", action_contract="")

    with pytest.raises(ValidationError, match="duplicate output"):
        ExecutionPlanStep(
            step_id="analyze",
            action_contract="code.analysis",
            outputs=("review", "review"),
        )


def test_iterated_step_requires_bound_input_and_declared_outputs() -> None:
    binding = InputBinding(
        parameter="item",
        source=PlanInputReference(input_name="items"),
    )
    step = ExecutionPlanStep(
        step_id="transform",
        action_contract="Transform",
        input_bindings=(binding,),
        outputs=("result",),
        iteration=Iteration(input_parameter="item"),
    )

    assert step.iteration == Iteration(input_parameter="item")
    with pytest.raises(ValidationError, match="exactly one bound input"):
        ExecutionPlanStep(
            step_id="transform",
            action_contract="Transform",
            input_bindings=(binding,),
            outputs=("result",),
            iteration=Iteration(input_parameter="missing"),
        )
    with pytest.raises(ValidationError, match="must declare output"):
        ExecutionPlanStep(
            step_id="transform",
            action_contract="Transform",
            input_bindings=(binding,),
            iteration=Iteration(input_parameter="item"),
        )


def test_plan_rejects_unknown_required_input_binding() -> None:
    with pytest.raises(ValidationError, match="unknown plan input"):
        ExecutionPlan(
            plan_id="review",
            workflow_id="review",
            workflow_version="1",
            required_inputs=("repository",),
            steps=(
                ExecutionPlanStep(
                    step_id="retrieve",
                    action_contract="repository.retrieve_changes",
                    input_bindings=(
                        InputBinding(
                            parameter="pull_request",
                            source=PlanInputReference(input_name="pull_request"),
                        ),
                    ),
                    outputs=("changes",),
                ),
            ),
            result=PlanResultReference(step_id="retrieve", output_name="changes"),
        )


def test_plan_rejects_unknown_step_and_self_references() -> None:
    for source, message in (
        (
            StepOutputReference(step_id="missing", output_name="changes"),
            "unknown step",
        ),
        (
            StepOutputReference(step_id="analyze", output_name="review"),
            "cannot reference itself",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            ExecutionPlan(
                plan_id="review",
                workflow_id="review",
                workflow_version="1",
                steps=(
                    ExecutionPlanStep(
                        step_id="analyze",
                        action_contract="code.analysis",
                        input_bindings=(
                            InputBinding(parameter="changes", source=source),
                        ),
                        outputs=("review",),
                    ),
                ),
                result=PlanResultReference(step_id="analyze", output_name="review"),
            )


def test_plan_rejects_future_step_reference() -> None:
    with pytest.raises(ValidationError, match="future step"):
        ExecutionPlan(
            plan_id="review",
            workflow_id="review",
            workflow_version="1",
            steps=(
                ExecutionPlanStep(
                    step_id="analyze",
                    action_contract="code.analysis",
                    input_bindings=(
                        InputBinding(
                            parameter="changes",
                            source=StepOutputReference(
                                step_id="retrieve",
                                output_name="changes",
                            ),
                        ),
                    ),
                    outputs=("review",),
                ),
                ExecutionPlanStep(
                    step_id="retrieve",
                    action_contract="repository.retrieve_changes",
                    outputs=("changes",),
                ),
            ),
            result=PlanResultReference(step_id="analyze", output_name="review"),
        )


def test_plan_rejects_missing_step_output() -> None:
    with pytest.raises(ValidationError, match="unknown output"):
        ExecutionPlan(
            plan_id="review",
            workflow_id="review",
            workflow_version="1",
            steps=(
                ExecutionPlanStep(
                    step_id="retrieve",
                    action_contract="repository.retrieve_changes",
                    outputs=("changes",),
                ),
                ExecutionPlanStep(
                    step_id="analyze",
                    action_contract="code.analysis",
                    input_bindings=(
                        InputBinding(
                            parameter="changes",
                            source=StepOutputReference(
                                step_id="retrieve",
                                output_name="missing",
                            ),
                        ),
                    ),
                    outputs=("review",),
                ),
            ),
            result=PlanResultReference(step_id="analyze", output_name="review"),
        )


@pytest.mark.parametrize(
    "result",
    [
        PlanResultReference(step_id="missing", output_name="review"),
        PlanResultReference(step_id="analyze", output_name="missing"),
    ],
)
def test_plan_rejects_invalid_result_reference(result: PlanResultReference) -> None:
    with pytest.raises(ValidationError, match="Plan result references unknown"):
        ExecutionPlan(
            plan_id="review",
            workflow_id="review",
            workflow_version="1",
            steps=(
                ExecutionPlanStep(
                    step_id="analyze",
                    action_contract="code.analysis",
                    outputs=("review",),
                ),
            ),
            result=result,
        )


def test_plan_and_nested_models_are_immutable() -> None:
    plan = valid_plan()

    with pytest.raises(ValidationError):
        plan.plan_id = "changed"

    with pytest.raises(ValidationError):
        plan.steps[0].action_contract = "changed"

    with pytest.raises(TypeError):
        plan.steps[0] = plan.steps[0]  # type: ignore[index]

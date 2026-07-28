import pytest

from app.execution import (
    ExecutionPlanConstructionError,
    ExecutionPlanner,
    InvalidWorkflowForPlanning,
    PlanInputReference,
    StepOutputReference,
    WorkflowSemanticError,
)
from app.workflows import (
    WorkflowDefinition,
    WorkflowInputBinding,
    WorkflowInputReference,
    WorkflowResultReference,
    WorkflowStepDefinition,
    WorkflowStepOutputReference,
)


def review_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="pull-request-review",
        name="Pull request review",
        version="1",
        required_inputs=("repository", "pull_request"),
        steps=(
            WorkflowStepDefinition(
                step_id="retrieve-changes",
                name="Retrieve changes",
                action_contract="repository.retrieve_changes",
                input_bindings=(
                    WorkflowInputBinding(
                        parameter="repository",
                        source=WorkflowInputReference(input_name="repository"),
                    ),
                    WorkflowInputBinding(
                        parameter="pull_request",
                        source=WorkflowInputReference(input_name="pull_request"),
                    ),
                ),
                outputs=("changes",),
            ),
            WorkflowStepDefinition(
                step_id="analyze-code",
                name="Analyze code",
                action_contract="code.analysis",
                input_bindings=(
                    WorkflowInputBinding(
                        parameter="changes",
                        source=WorkflowStepOutputReference(
                            step_id="retrieve-changes",
                            output_name="changes",
                        ),
                    ),
                ),
                outputs=("review",),
            ),
        ),
        result=WorkflowResultReference(
            step_id="analyze-code",
            output_name="review",
        ),
    )


def test_planner_compiles_workflow_intent_into_an_execution_plan() -> None:
    workflow = review_workflow()

    plan = ExecutionPlanner().plan(workflow)

    assert plan.plan_id == "pull-request-review.1"
    assert plan.workflow_id == workflow.workflow_id
    assert plan.workflow_version == workflow.version
    assert plan.required_inputs == workflow.required_inputs
    assert tuple(step.step_id for step in plan.steps) == (
        "retrieve-changes",
        "analyze-code",
    )
    assert plan.steps[0].action_contract == "repository.retrieve_changes"
    assert plan.steps[0].input_bindings[0].source == PlanInputReference(
        input_name="repository"
    )
    assert plan.steps[1].input_bindings[0].source == StepOutputReference(
        step_id="retrieve-changes",
        output_name="changes",
    )
    assert plan.result.step_id == "analyze-code"
    assert plan.result.output_name == "review"


def test_planning_is_deterministic_and_does_not_modify_the_workflow() -> None:
    workflow = review_workflow()
    original = workflow.model_dump()
    planner = ExecutionPlanner()

    first = planner.plan(workflow)
    second = planner.plan(workflow)

    assert first == second
    assert first.model_dump() == second.model_dump()
    assert workflow.model_dump() == original


@pytest.mark.parametrize(
    ("workflow", "message"),
    [
        (
            WorkflowDefinition(
                workflow_id="empty",
                name="Empty",
                version="1",
                result=WorkflowResultReference(step_id="missing", output_name="result"),
            ),
            "at least one step",
        ),
        (
            WorkflowDefinition(
                workflow_id="missing-result",
                name="Missing result",
                version="1",
                steps=(
                    WorkflowStepDefinition(
                        step_id="only",
                        name="Only",
                        action_contract="work.perform",
                        outputs=("result",),
                    ),
                ),
            ),
            "result reference",
        ),
        (
            WorkflowDefinition(
                workflow_id="missing-contract",
                name="Missing contract",
                version="1",
                steps=(WorkflowStepDefinition(step_id="only", name="Only"),),
                result=WorkflowResultReference(step_id="only", output_name="result"),
            ),
            "action contract",
        ),
    ],
)
def test_planner_rejects_invalid_workflow_definitions(
    workflow: WorkflowDefinition,
    message: str,
) -> None:
    with pytest.raises(InvalidWorkflowForPlanning, match=message):
        ExecutionPlanner().plan(workflow)


def test_planner_rejects_duplicate_steps_inputs_outputs_and_parameters() -> None:
    step = WorkflowStepDefinition(
        step_id="same",
        name="Same",
        action_contract="work.perform",
        input_bindings=(
            WorkflowInputBinding(
                parameter="value",
                source=WorkflowInputReference(input_name="input"),
            ),
            WorkflowInputBinding(
                parameter="value",
                source=WorkflowInputReference(input_name="input"),
            ),
        ),
        outputs=("result", "result"),
    )
    workflow = WorkflowDefinition(
        workflow_id="duplicates",
        name="Duplicates",
        version="1",
        required_inputs=("input", "input"),
        steps=(step, step),
        result=WorkflowResultReference(step_id="same", output_name="result"),
    )

    with pytest.raises(InvalidWorkflowForPlanning, match="duplicate step"):
        ExecutionPlanner().plan(workflow)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (WorkflowInputReference(input_name="missing"), "unknown workflow input"),
        (
            WorkflowStepOutputReference(step_id="missing", output_name="value"),
            "unknown step",
        ),
        (
            WorkflowStepOutputReference(step_id="produce", output_name="missing"),
            "unknown output",
        ),
    ],
)
def test_planner_rejects_invalid_internal_references(
    source: WorkflowInputReference | WorkflowStepOutputReference,
    message: str,
) -> None:
    workflow = WorkflowDefinition(
        workflow_id="invalid-reference",
        name="Invalid reference",
        version="1",
        required_inputs=("declared",),
        steps=(
            WorkflowStepDefinition(
                step_id="produce",
                name="Produce",
                action_contract="value.produce",
                outputs=("value",),
            ),
            WorkflowStepDefinition(
                step_id="consume",
                name="Consume",
                action_contract="value.consume",
                input_bindings=(
                    WorkflowInputBinding(parameter="value", source=source),
                ),
                outputs=("result",),
            ),
        ),
        result=WorkflowResultReference(step_id="consume", output_name="result"),
    )

    with pytest.raises(WorkflowSemanticError, match=message):
        ExecutionPlanner().plan(workflow)


def test_planner_rejects_future_step_references() -> None:
    workflow = WorkflowDefinition(
        workflow_id="future-reference",
        name="Future reference",
        version="1",
        steps=(
            WorkflowStepDefinition(
                step_id="consume",
                name="Consume",
                action_contract="value.consume",
                input_bindings=(
                    WorkflowInputBinding(
                        parameter="value",
                        source=WorkflowStepOutputReference(
                            step_id="produce",
                            output_name="value",
                        ),
                    ),
                ),
                outputs=("result",),
            ),
            WorkflowStepDefinition(
                step_id="produce",
                name="Produce",
                action_contract="value.produce",
                outputs=("value",),
            ),
        ),
        result=WorkflowResultReference(step_id="consume", output_name="result"),
    )

    with pytest.raises(WorkflowSemanticError, match="future step"):
        ExecutionPlanner().plan(workflow)


def test_planner_rejects_cyclic_dependencies() -> None:
    workflow = WorkflowDefinition(
        workflow_id="cycle",
        name="Cycle",
        version="1",
        steps=(
            WorkflowStepDefinition(
                step_id="first",
                name="First",
                action_contract="work.first",
                input_bindings=(
                    WorkflowInputBinding(
                        parameter="second",
                        source=WorkflowStepOutputReference(
                            step_id="second",
                            output_name="second",
                        ),
                    ),
                ),
                outputs=("first",),
            ),
            WorkflowStepDefinition(
                step_id="second",
                name="Second",
                action_contract="work.second",
                input_bindings=(
                    WorkflowInputBinding(
                        parameter="first",
                        source=WorkflowStepOutputReference(
                            step_id="first",
                            output_name="first",
                        ),
                    ),
                ),
                outputs=("second",),
            ),
        ),
        result=WorkflowResultReference(step_id="second", output_name="second"),
    )

    with pytest.raises(WorkflowSemanticError, match="cyclic"):
        ExecutionPlanner().plan(workflow)


def test_planner_rejects_invalid_result_and_unreachable_steps() -> None:
    invalid_result = review_workflow().model_copy(
        update={
            "result": WorkflowResultReference(
                step_id="analyze-code",
                output_name="missing",
            )
        }
    )
    with pytest.raises(WorkflowSemanticError, match="result references unknown output"):
        ExecutionPlanner().plan(invalid_result)

    unreachable = review_workflow().model_copy(
        update={
            "steps": (
                WorkflowStepDefinition(
                    step_id="unused",
                    name="Unused",
                    action_contract="work.unused",
                    outputs=("unused",),
                ),
                *review_workflow().steps,
            )
        }
    )
    with pytest.raises(WorkflowSemanticError, match="do not contribute"):
        ExecutionPlanner().plan(unreachable)


def test_plan_construction_failures_have_a_distinct_error() -> None:
    workflow = review_workflow().model_copy(
        update={
            "workflow_id": "pull/request/review",
        }
    )

    with pytest.raises(ExecutionPlanConstructionError):
        ExecutionPlanner().plan(workflow)

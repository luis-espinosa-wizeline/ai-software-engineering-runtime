import pytest

from app.shared import JsonValue
from app.workflows import (
    InvalidWorkflowInputType,
    MissingWorkflowInput,
    UnexpectedWorkflowInputs,
    WorkflowDefinition,
    WorkflowInputDefinition,
    WorkflowInputType,
    WorkflowInputValidator,
)


def workflow(
    *definitions: WorkflowInputDefinition,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="typed-workflow",
        name="Typed workflow",
        version="3",
        inputs=definitions,
    )


def definition(
    name: str,
    input_type: WorkflowInputType,
    *,
    required: bool = True,
) -> WorkflowInputDefinition:
    return WorkflowInputDefinition(
        name=name,
        type=input_type,
        required=required,
    )


@pytest.mark.parametrize(
    ("input_type", "value"),
    [
        (WorkflowInputType.STRING, "value"),
        (WorkflowInputType.INTEGER, 42),
        (WorkflowInputType.BOOLEAN, True),
        (WorkflowInputType.NUMBER, 1.5),
        (WorkflowInputType.NUMBER, 42),
        (WorkflowInputType.OBJECT, {"key": "value"}),
        (WorkflowInputType.ARRAY, ["first", 2]),
    ],
)
def test_validator_accepts_supported_structural_values(
    input_type: WorkflowInputType,
    value: JsonValue,
) -> None:
    inputs = {"value": value}

    validated = WorkflowInputValidator().validate(
        workflow(definition("value", input_type)),
        inputs,
    )

    assert validated == inputs
    assert validated is not inputs


def test_validator_accepts_an_omitted_optional_unbound_input() -> None:
    validated = WorkflowInputValidator().validate(
        workflow(
            definition("required", WorkflowInputType.STRING),
            definition("optional", WorkflowInputType.STRING, required=False),
        ),
        {"required": "value"},
    )

    assert validated == {"required": "value"}


def test_validator_rejects_missing_required_input_with_workflow_context() -> None:
    with pytest.raises(
        MissingWorkflowInput,
        match="typed-workflow.*'3'.*'repository'.*'string'.*missing",
    ):
        WorkflowInputValidator().validate(
            workflow(definition("repository", WorkflowInputType.STRING)),
            {},
        )


def test_validator_rejects_unexpected_inputs_deterministically() -> None:
    with pytest.raises(
        UnexpectedWorkflowInputs,
        match="typed-workflow.*'3'.*'alpha'.*'zeta'",
    ):
        WorkflowInputValidator().validate(
            workflow(definition("expected", WorkflowInputType.STRING)),
            {"expected": "value", "zeta": 1, "alpha": 2},
        )


@pytest.mark.parametrize(
    ("input_type", "value", "actual_type"),
    [
        (WorkflowInputType.STRING, 42, "integer"),
        (WorkflowInputType.INTEGER, "42", "string"),
        (WorkflowInputType.INTEGER, True, "boolean"),
        (WorkflowInputType.NUMBER, True, "boolean"),
        (WorkflowInputType.BOOLEAN, 1, "integer"),
        (WorkflowInputType.OBJECT, [], "array"),
        (WorkflowInputType.ARRAY, {}, "object"),
        (WorkflowInputType.STRING, None, "null"),
    ],
)
def test_validator_rejects_incorrect_types_without_coercion(
    input_type: WorkflowInputType,
    value: JsonValue,
    actual_type: str,
) -> None:
    with pytest.raises(
        InvalidWorkflowInputType,
        match=rf"'value'.*'{input_type.value}'.*'{actual_type}'",
    ):
        WorkflowInputValidator().validate(
            workflow(definition("value", input_type)),
            {"value": value},
        )

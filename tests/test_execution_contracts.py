from typing import assert_type

import pytest
from pydantic import ValidationError

from app.capabilities import Capability, CapabilityRequest, CapabilityResult
from app.execution import Artifact


class ReviewCapability:
    """Minimal executable used to verify the structural capability contract."""

    @property
    def action_contract(self) -> str:
        return "code.review"

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        repository = request.inputs["repository"]
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="review",
                    payload={"repository": repository, "approved": True},
                ),
            )
        )


def accepts_capability(capability: Capability) -> Capability:
    return capability


class MissingExecute:
    @property
    def action_contract(self) -> str:
        return "code.review"


def test_capability_request_contains_only_contract_and_resolved_inputs() -> None:
    request = CapabilityRequest(
        action_contract="code.review",
        inputs={
            "repository": "example/runtime",
            "changes": {"files": ["app/main.py"]},
        },
    )

    assert request.action_contract == "code.review"
    assert request.inputs == {
        "repository": "example/runtime",
        "changes": {"files": ["app/main.py"]},
    }
    assert request.model_dump() == {
        "action_contract": "code.review",
        "inputs": {
            "repository": "example/runtime",
            "changes": {"files": ["app/main.py"]},
        },
    }


def test_capability_result_transports_one_or_more_artifacts() -> None:
    review = Artifact(name="review", payload="Approved")
    summary = Artifact(name="summary", payload={"findings": 0})

    result = CapabilityResult(artifacts=(review, summary))

    assert result.artifacts == (review, summary)
    assert result.artifacts[0] is review
    assert result.artifacts[1] is summary


def test_capability_result_requires_an_artifact() -> None:
    with pytest.raises(ValidationError):
        CapabilityResult(artifacts=())


def test_execution_contracts_are_immutable_and_strict() -> None:
    request = CapabilityRequest(action_contract="code.review")
    result = CapabilityResult(artifacts=(Artifact(name="review", payload="Approved"),))

    with pytest.raises(ValidationError):
        request.action_contract = "changed"

    with pytest.raises(ValidationError):
        result.artifacts = ()

    with pytest.raises(ValidationError):
        CapabilityRequest(
            action_contract="code.review",
            inputs={},
            execution_context={},
        )  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        CapabilityResult(
            artifacts=result.artifacts,
            status="succeeded",
        )  # type: ignore[call-arg]


@pytest.mark.parametrize("action_contract", ["", "code/review", ".code-review"])
def test_action_contract_must_be_a_valid_provider_neutral_identifier(
    action_contract: str,
) -> None:
    with pytest.raises(ValidationError):
        CapabilityRequest(action_contract=action_contract)


def test_capability_contract_transforms_request_into_artifacts() -> None:
    capability = accepts_capability(ReviewCapability())
    assert_type(capability, Capability)
    assert isinstance(ReviewCapability(), Capability)
    assert not isinstance(MissingExecute(), Capability)
    request = CapabilityRequest(
        action_contract=capability.action_contract,
        inputs={"repository": "example/runtime"},
    )

    result = capability.execute(request)

    assert result == CapabilityResult(
        artifacts=(
            Artifact(
                name="review",
                payload={
                    "repository": "example/runtime",
                    "approved": True,
                },
            ),
        )
    )

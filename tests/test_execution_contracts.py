from typing import assert_type

import pytest
from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    Capability,
    CapabilityImplementation,
    CapabilityRequest,
    CapabilityResult,
)
from app.capabilities.identity import IdentityCapabilityImplementation
from tests.capability_fixtures import capability


class ReviewImplementation:
    """Minimal executable used to verify the structural implementation contract."""

    @property
    def capability(self) -> Capability:
        return capability("code.review")

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        repository = request.artifact("repository")
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="review",
                    payload={"repository": repository.payload, "approved": True},
                ),
            )
        )


class MissingExecute:
    @property
    def capability(self) -> Capability:
        return capability("code.review")


def accepts_implementation(
    implementation: CapabilityImplementation,
) -> CapabilityImplementation:
    return implementation


def test_capability_defines_what_without_execution_behavior() -> None:
    value = capability("code.review")

    assert value.contract == "code.review"
    assert value.name == "code.review"
    assert not hasattr(value, "execute")
    with pytest.raises(ValidationError):
        value.contract = "changed"


def test_capability_request_contains_only_capability_and_input_artifacts() -> None:
    repository = Artifact(name="repository", payload="example/runtime")
    changes = Artifact(name="changes", payload={"files": ["app/main.py"]})
    request = CapabilityRequest(
        capability=capability("code.review"),
        artifacts=(repository, changes),
    )

    assert request.artifacts == (repository, changes)
    assert request.artifact("repository") is repository
    assert set(request.model_dump()) == {"capability", "artifacts"}


def test_capability_request_requires_unique_named_input_artifacts() -> None:
    with pytest.raises(ValidationError, match="names must be unique"):
        CapabilityRequest(
            capability=capability("example"),
            artifacts=(
                Artifact(name="value", payload=1),
                Artifact(name="value", payload=2),
            ),
        )

    request = CapabilityRequest(capability=capability("example"))
    with pytest.raises(ValueError, match="was not provided"):
        request.artifact("missing")


def test_capability_result_transports_one_or_more_artifacts() -> None:
    review = Artifact(name="review", payload="Approved")
    summary = Artifact(name="summary", payload={"findings": 0})

    result = CapabilityResult(artifacts=(review, summary))

    assert result.artifacts == (review, summary)
    with pytest.raises(ValidationError):
        CapabilityResult(artifacts=())


def test_execution_contracts_are_immutable_and_strict() -> None:
    value = capability("code.review")
    request = CapabilityRequest(capability=value)
    result = CapabilityResult(artifacts=(Artifact(name="review", payload="Approved"),))

    with pytest.raises(ValidationError):
        request.artifacts = ()
    with pytest.raises(ValidationError):
        result.artifacts = ()
    with pytest.raises(ValidationError):
        CapabilityRequest(
            capability=value,
            artifacts=(),
            execution_context={},
        )  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        CapabilityResult(
            artifacts=result.artifacts,
            provider="openai",
        )  # type: ignore[call-arg]


@pytest.mark.parametrize("contract", ["", "code/review", ".code-review"])
def test_capability_contract_must_be_provider_neutral_identifier(contract: str) -> None:
    with pytest.raises(ValidationError):
        capability(contract)


def test_implementation_contract_transforms_artifacts_into_artifacts() -> None:
    implementation = accepts_implementation(ReviewImplementation())
    assert_type(implementation, CapabilityImplementation)
    assert isinstance(ReviewImplementation(), CapabilityImplementation)
    assert not isinstance(MissingExecute(), CapabilityImplementation)
    request = CapabilityRequest(
        capability=implementation.capability,
        artifacts=(Artifact(name="repository", payload="example/runtime"),),
    )

    result = implementation.execute(request)

    assert result.artifacts[0].payload == {
        "repository": "example/runtime",
        "approved": True,
    }


def test_identity_implementation_provides_minimal_working_execution() -> None:
    implementation = IdentityCapabilityImplementation()
    request = CapabilityRequest(
        capability=implementation.capability,
        artifacts=(Artifact(name="value", payload={"answer": 42}),),
    )

    assert implementation.execute(request) == CapabilityResult(
        artifacts=(Artifact(name="result", payload={"answer": 42}),)
    )

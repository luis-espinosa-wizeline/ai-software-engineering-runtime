from uuid import UUID

import pytest
from pydantic import ValidationError

from app.execution import (
    Artifact,
    ArtifactAlreadyStored,
    ArtifactNotFound,
    ExecutionContext,
)

EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000001")


def make_context() -> ExecutionContext:
    return ExecutionContext(
        execution_id=EXECUTION_ID,
        plan_id="pull-request-review.1",
        inputs={"repository": "example/runtime", "pull_request": 42},
    )


def test_artifact_creation_preserves_provider_neutral_content() -> None:
    artifact = Artifact(
        name="review",
        payload={"summary": "No issues", "findings": []},
        metadata={"format": "application/json", "publish": True},
    )

    assert artifact.name == "review"
    assert artifact.payload == {"summary": "No issues", "findings": []}
    assert artifact.metadata == {
        "format": "application/json",
        "publish": True,
    }


def test_artifact_is_minimal_immutable_and_strict() -> None:
    artifact = Artifact(name="changes", payload="diff")

    with pytest.raises(ValidationError):
        artifact.name = "renamed"

    with pytest.raises(ValidationError):
        Artifact(name="changes", payload="diff", provider="github")  # type: ignore[call-arg]


def test_context_exposes_execution_identity_and_inputs() -> None:
    context = make_context()

    assert context.execution_id == EXECUTION_ID
    assert context.plan_id == "pull-request-review.1"
    assert context.inputs == {
        "repository": "example/runtime",
        "pull_request": 42,
    }


def test_context_stores_and_retrieves_artifacts_by_step_and_name() -> None:
    context = make_context()
    changes = Artifact(name="changes", payload={"files": ["app/main.py"]})
    review = Artifact(name="review", payload="Looks good")

    context.store_artifact("retrieve-changes", changes)
    context.store_artifact("analyze-code", review)

    assert context.has_artifact("retrieve-changes", "changes")
    assert context.has_artifact("analyze-code", "review")
    assert context.get_artifact("retrieve-changes", "changes") is changes
    assert context.get_artifact("analyze-code", "review") is review


def test_same_artifact_name_is_independent_between_steps() -> None:
    context = make_context()
    first = Artifact(name="result", payload="first")
    second = Artifact(name="result", payload="second")

    context.store_artifact("first-step", first)
    context.store_artifact("second-step", second)

    assert context.get_artifact("first-step", "result") is first
    assert context.get_artifact("second-step", "result") is second


def test_duplicate_artifact_cannot_overwrite_existing_output() -> None:
    context = make_context()
    original = Artifact(name="review", payload="original")

    context.store_artifact("analyze-code", original)

    with pytest.raises(ArtifactAlreadyStored, match="already stored"):
        context.store_artifact(
            "analyze-code",
            Artifact(name="review", payload="replacement"),
        )

    assert context.get_artifact("analyze-code", "review") is original


@pytest.mark.parametrize(
    ("step_id", "artifact_name"),
    [
        ("missing-step", "review"),
        ("analyze-code", "missing-artifact"),
    ],
)
def test_missing_artifact_behavior_is_explicit(
    step_id: str,
    artifact_name: str,
) -> None:
    context = make_context()
    context.store_artifact(
        "analyze-code",
        Artifact(name="review", payload="complete"),
    )

    assert not context.has_artifact(step_id, artifact_name)
    with pytest.raises(ArtifactNotFound, match="was not found"):
        context.get_artifact(step_id, artifact_name)


def test_artifact_storage_and_retrieval_are_deterministic() -> None:
    first = make_context()
    second = make_context()
    artifacts = (
        ("retrieve-changes", Artifact(name="changes", payload="diff")),
        ("analyze-code", Artifact(name="review", payload="approved")),
    )

    for step_id, artifact in artifacts:
        first.store_artifact(step_id, artifact)
        second.store_artifact(step_id, artifact)

    for step_id, artifact in artifacts:
        assert first.get_artifact(step_id, artifact.name) == second.get_artifact(
            step_id,
            artifact.name,
        )

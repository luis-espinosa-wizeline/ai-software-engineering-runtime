from typing import Any

import pytest

from app.capabilities import (
    Artifact,
    CapabilityRequest,
    EngineeringFinding,
    EngineeringFindings,
    FindingSeverity,
)
from app.capabilities.merge_engineering_findings import (
    MergeEngineeringFindingsImplementation,
)


def finding(summary: str, severity: FindingSeverity) -> EngineeringFinding:
    return EngineeringFinding(
        summary=summary,
        source_file=f"{summary}.py",
        severity=severity,
        confidence=0.9,
        category="test",
        explanation=f"Explanation for {summary}.",
        recommendation=f"Recommendation for {summary}.",
    )


def merge_request(
    implementation: MergeEngineeringFindingsImplementation,
    collection: list[Any],
) -> CapabilityRequest:
    return CapabilityRequest(
        capability=implementation.capability,
        artifacts=(Artifact(name="engineering_findings", payload=collection),),
    )


def test_merge_preserves_outer_and_inner_finding_order_without_modification() -> None:
    first = EngineeringFindings(
        findings=(
            finding("first", FindingSeverity.HIGH),
            finding("second", FindingSeverity.LOW),
        )
    )
    second = EngineeringFindings(
        findings=(finding("third", FindingSeverity.CRITICAL),)
    )
    implementation = MergeEngineeringFindingsImplementation()
    original = (first.model_dump(), second.model_dump())

    result = implementation.execute(
        merge_request(
            implementation,
            [first.model_dump(mode="json"), second.model_dump(mode="json")],
        )
    )

    merged = EngineeringFindings.model_validate(result.artifacts[0].payload)
    assert merged.findings == first.findings + second.findings
    assert tuple(item.summary for item in merged.findings) == (
        "first",
        "second",
        "third",
    )
    assert (first.model_dump(), second.model_dump()) == original
    assert result.artifacts[0].name == "engineering_findings"


def test_merge_is_deterministic() -> None:
    implementation = MergeEngineeringFindingsImplementation()
    request = merge_request(
        implementation,
        [
            EngineeringFindings(
                findings=(finding("stable", FindingSeverity.MEDIUM),)
            ).model_dump(mode="json")
        ],
    )

    assert implementation.execute(request) == implementation.execute(request)


def test_merge_supports_empty_collections_and_empty_findings() -> None:
    implementation = MergeEngineeringFindingsImplementation()

    empty_collection = implementation.execute(merge_request(implementation, []))
    empty_documents = implementation.execute(
        merge_request(
            implementation,
            [
                EngineeringFindings().model_dump(mode="json"),
                EngineeringFindings().model_dump(mode="json"),
            ],
        )
    )

    expected = Artifact(name="engineering_findings", payload={"findings": []})
    assert empty_collection.artifacts == (expected,)
    assert empty_documents.artifacts == (expected,)


@pytest.mark.parametrize(
    "payload",
    [
        {"findings": []},
        ["not findings"],
        [{"findings": "not a list"}],
        [{"findings": [{"summary": "incomplete"}]}],
    ],
)
def test_merge_rejects_invalid_collections(payload: Any) -> None:
    implementation = MergeEngineeringFindingsImplementation()
    request = CapabilityRequest(
        capability=implementation.capability,
        artifacts=(Artifact(name="engineering_findings", payload=payload),),
    )

    with pytest.raises(ValueError, match="EngineeringFindings"):
        implementation.execute(request)

import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from app.capabilities import (
    Artifact,
    Capability,
    CapabilityRequest,
    CapabilityResult,
    InMemoryCapabilityResolver,
)
from app.capabilities.analyze_source_code import (
    AnalyzeSourceCodeOllamaImplementation,
    EngineeringFindings,
)
from app.capabilities.merge_engineering_findings import (
    MergeEngineeringFindingsImplementation,
)
from app.capabilities.read_changed_files import ReadChangedFilesImplementation
from app.capabilities.read_file import ReadFileImplementation
from app.execution import (
    ExecutionContext,
    ExecutionEngine,
    ExecutionPlan,
    ExecutionPlanStep,
    InputBinding,
    Iteration,
    IterationInputNotCollection,
    IterationOutputMismatch,
    PlanInputReference,
    PlanResultReference,
    StepOutputReference,
)
from app.shared import JsonValue
from tests.capability_fixtures import capability

EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000009")


class ChangedFileReader:
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def read_pull_request(
        self, repository: str, pull_request_number: int
    ) -> dict[str, JsonValue]:
        raise AssertionError("Pull-request metadata is not used by this test")

    def read_changed_files(
        self, repository: str, pull_request_number: int
    ) -> list[JsonValue]:
        return list(self._paths)


class ResultImplementation:
    def __init__(
        self,
        contract: str,
        output_name: str,
        *,
        actual_output_name: str | None = None,
    ) -> None:
        self._capability = capability(contract)
        self._output_name = output_name
        self._actual_output_name = actual_output_name or output_name
        self.requests: list[CapabilityRequest] = []

    @property
    def capability(self) -> Capability:
        return self._capability

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self.requests.append(request)
        value = request.artifacts[0].payload
        return CapabilityResult(
            artifacts=(
                Artifact(name=self._actual_output_name, payload={"value": value}),
            )
        )


def iteration_plan(collection_input: str = "items") -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="iteration.1",
        workflow_id="iteration",
        workflow_version="1",
        required_inputs=(collection_input,),
        steps=(
            ExecutionPlanStep(
                step_id="transform",
                action_contract="Transform",
                input_bindings=(
                    InputBinding(
                        parameter="item",
                        source=PlanInputReference(input_name=collection_input),
                    ),
                ),
                outputs=("result",),
                iteration=Iteration(input_parameter="item"),
            ),
        ),
        result=PlanResultReference(step_id="transform", output_name="result"),
    )


def context(plan: ExecutionPlan, inputs: dict[str, JsonValue]) -> ExecutionContext:
    return ExecutionContext(
        execution_id=EXECUTION_ID,
        plan_id=plan.plan_id,
        inputs=inputs,
    )


def test_iteration_preserves_order_and_aggregates_output_payloads() -> None:
    plan = iteration_plan()
    implementation = ResultImplementation("Transform", "result")

    result = ExecutionEngine(
        InMemoryCapabilityResolver((implementation,))
    ).execute(plan, context(plan, {"items": ["first", "second", "third"]}))

    assert tuple(
        request.artifact("item").payload for request in implementation.requests
    ) == ("first", "second", "third")
    assert result == Artifact(
        name="result",
        payload=[
            {"value": "first"},
            {"value": "second"},
            {"value": "third"},
        ],
    )


def test_empty_iteration_produces_declared_empty_collections() -> None:
    plan = iteration_plan()
    implementation = ResultImplementation("Transform", "result")

    result = ExecutionEngine(
        InMemoryCapabilityResolver((implementation,))
    ).execute(plan, context(plan, {"items": []}))

    assert implementation.requests == []
    assert result == Artifact(name="result", payload=[])


def test_iteration_rejects_non_collection_input() -> None:
    plan = iteration_plan()
    implementation = ResultImplementation("Transform", "result")

    with pytest.raises(IterationInputNotCollection, match="item.*list"):
        ExecutionEngine(InMemoryCapabilityResolver((implementation,))).execute(
            plan,
            context(plan, {"items": "not a collection"}),
        )

    assert implementation.requests == []


def test_iteration_requires_each_invocation_to_produce_declared_outputs() -> None:
    plan = iteration_plan()
    implementation = ResultImplementation(
        "Transform",
        "result",
        actual_output_name="unexpected",
    )

    with pytest.raises(IterationOutputMismatch, match="Iteration 0.*unexpected"):
        ExecutionEngine(InMemoryCapabilityResolver((implementation,))).execute(
            plan,
            context(plan, {"items": ["first"]}),
        )


def test_changed_files_compose_through_two_ordered_iterations(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("FIRST = 1\n", encoding="utf-8")
    second.write_text("SECOND = 2\n", encoding="utf-8")
    changed_files = ReadChangedFilesImplementation(
        ChangedFileReader([str(first), str(second)])
    )
    read_file = ReadFileImplementation()
    analyzed_sources: list[str] = []

    def analyze(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompt: str = body["messages"][1]["content"]
        source_marker = "FIRST" if "FIRST = 1" in prompt else "SECOND"
        analyzed_sources.append(source_marker)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "findings": [
                                {
                                    "summary": f"{source_marker} finding",
                                    "source_file": "model.py",
                                    "severity": "info",
                                    "confidence": 1.0,
                                    "category": "test",
                                    "explanation": f"Analyzed {source_marker}.",
                                    "recommendation": "Keep testing.",
                                }
                            ]
                        }
                    ),
                }
            },
        )

    analyzer = AnalyzeSourceCodeOllamaImplementation(
        "test-model",
        client=httpx.Client(
            base_url="http://ollama.test",
            transport=httpx.MockTransport(analyze),
        ),
    )
    plan = ExecutionPlan(
        plan_id="changed-files.1",
        workflow_id="changed-files",
        workflow_version="1",
        required_inputs=("repository", "pull_request_number"),
        steps=(
            ExecutionPlanStep(
                step_id="changed-files",
                action_contract="ReadChangedFiles",
                input_bindings=(
                    InputBinding(
                        parameter="repository",
                        source=PlanInputReference(input_name="repository"),
                    ),
                    InputBinding(
                        parameter="pull_request_number",
                        source=PlanInputReference(input_name="pull_request_number"),
                    ),
                ),
                outputs=("changed_files",),
            ),
            ExecutionPlanStep(
                step_id="read-files",
                action_contract="ReadFile",
                input_bindings=(
                    InputBinding(
                        parameter="path",
                        source=StepOutputReference(
                            step_id="changed-files",
                            output_name="changed_files",
                        ),
                    ),
                ),
                outputs=("SourceCode",),
                iteration=Iteration(input_parameter="path"),
            ),
            ExecutionPlanStep(
                step_id="analyze-files",
                action_contract="AnalyzeSourceCode",
                input_bindings=(
                    InputBinding(
                        parameter="SourceCode",
                        source=StepOutputReference(
                            step_id="read-files",
                            output_name="SourceCode",
                        ),
                    ),
                ),
                outputs=("engineering_findings",),
                iteration=Iteration(input_parameter="SourceCode"),
            ),
            ExecutionPlanStep(
                step_id="merge-findings",
                action_contract="MergeEngineeringFindings",
                input_bindings=(
                    InputBinding(
                        parameter="engineering_findings",
                        source=StepOutputReference(
                            step_id="analyze-files",
                            output_name="engineering_findings",
                        ),
                    ),
                ),
                outputs=("engineering_findings",),
            ),
        ),
        result=PlanResultReference(
            step_id="merge-findings",
            output_name="engineering_findings",
        ),
    )
    execution_context = context(
        plan,
        {"repository": "example/runtime", "pull_request_number": 42},
    )

    result = ExecutionEngine(
        InMemoryCapabilityResolver(
            (
                changed_files,
                read_file,
                analyzer,
                MergeEngineeringFindingsImplementation(),
            )
        )
    ).execute(plan, execution_context)

    assert analyzed_sources == ["FIRST", "SECOND"]
    collected = execution_context.get_artifact(
        "analyze-files", "engineering_findings"
    )
    assert isinstance(collected.payload, list)
    parsed = tuple(
        EngineeringFindings.model_validate(findings)
        for findings in collected.payload
    )
    assert tuple(item.findings[0].summary for item in parsed) == (
        "FIRST finding",
        "SECOND finding",
    )
    assert result.name == "engineering_findings"
    merged = EngineeringFindings.model_validate(result.payload)
    assert tuple(item.summary for item in merged.findings) == (
        "FIRST finding",
        "SECOND finding",
    )

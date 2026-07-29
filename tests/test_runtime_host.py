from collections.abc import Iterator, Mapping
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    CapabilityResolver,
    InMemoryCapabilityResolver,
)
from app.capabilities.identity import IdentityCapabilityImplementation
from app.execution import (
    ExecutionContext,
    ExecutionEngine,
    ExecutionPlan,
    ExecutionPlanner,
)
from app.host import (
    CapabilityComposition,
    ExecutionContextFactory,
    HostEvent,
    InMemoryWorkflowSelector,
    RuntimeHost,
    UnsupportedHostEvent,
    WorkflowRoute,
)
from app.shared import JsonValue
from app.workflows import InvalidWorkflowInputType, WorkflowDefinition

FIRST_EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000010")
SECOND_EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000011")


def write_project(root: Path) -> None:
    (root / "workflows").mkdir()
    (root / "runtime.yaml").write_text(
        "name: Host test project\nversion: 1\n",
        encoding="utf-8",
    )
    (root / "workflows" / "identity.yaml").write_text(
        """
name: identity
version: "7"
inputs:
  value:
    type: string
steps:
  - id: identity
    action: Identity
    inputs:
      value:
        workflow_input: value
    outputs: [result]
result:
  step: identity
  artifact: result
""",
        encoding="utf-8",
    )


def test_workflow_selector_preserves_configured_route() -> None:
    route = WorkflowRoute(workflow_id="review", workflow_version="2026.1")
    selector = InMemoryWorkflowSelector({"pull_request": route})

    selected = selector.select(
        HostEvent(event_kind="pull_request", inputs={"repository": "example/runtime"})
    )

    assert selected is route
    assert selected.workflow_id == "review"
    assert selected.workflow_version == "2026.1"


def test_workflow_selector_rejects_unsupported_event_kind() -> None:
    selector = InMemoryWorkflowSelector(
        {"pull_request": WorkflowRoute(workflow_id="review", workflow_version="1")}
    )

    with pytest.raises(UnsupportedHostEvent, match="command"):
        selector.select(HostEvent(event_kind="command", inputs={}))


def test_host_event_and_workflow_route_are_immutable_and_strict() -> None:
    event = HostEvent(event_kind="command", event_id="delivery-1", inputs={})
    route = WorkflowRoute(workflow_id="identity", workflow_version="1")

    with pytest.raises(ValidationError):
        event.event_kind = "changed"
    with pytest.raises(ValidationError):
        route.workflow_version = "2"
    with pytest.raises(ValidationError):
        HostEvent(event_kind=" ", inputs={})


class RecordingComposition(CapabilityComposition):
    def __init__(self, resolver: CapabilityResolver) -> None:
        self._resolver = resolver
        self.calls: list[tuple[HostEvent, WorkflowDefinition]] = []

    def compose(
        self,
        event: HostEvent,
        workflow: WorkflowDefinition,
    ) -> CapabilityResolver:
        self.calls.append((event, workflow))
        return self._resolver


class RecordingPlanner(ExecutionPlanner):
    def __init__(self) -> None:
        self.calls: list[WorkflowDefinition] = []

    def plan(self, workflow: WorkflowDefinition) -> ExecutionPlan:
        self.calls.append(workflow)
        return super().plan(workflow)


class RecordingContextFactory(ExecutionContextFactory):
    def __init__(self, execution_ids: Iterator[UUID]) -> None:
        super().__init__(lambda: next(execution_ids))
        self.calls: list[tuple[ExecutionPlan, dict[str, JsonValue]]] = []

    def create(
        self,
        plan: ExecutionPlan,
        inputs: Mapping[str, JsonValue],
    ) -> ExecutionContext:
        self.calls.append((plan, dict(inputs)))
        return super().create(plan, inputs)


class RecordingEngine(ExecutionEngine):
    def __init__(self, resolver: CapabilityResolver) -> None:
        super().__init__(resolver)
        self.calls: list[tuple[ExecutionPlan, ExecutionContext]] = []

    def execute(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> Artifact:
        self.calls.append((plan, context))
        return super().execute(plan, context)


def test_runtime_host_delegates_one_execution_to_existing_core(tmp_path: Path) -> None:
    write_project(tmp_path)
    event = HostEvent(
        event_kind="command",
        event_id="delivery-7",
        inputs={"value": "unchanged"},
        metadata={"correlation_id": "correlation-1"},
    )
    selector = InMemoryWorkflowSelector(
        {"command": WorkflowRoute(workflow_id="identity", workflow_version="7")}
    )
    resolver = InMemoryCapabilityResolver((IdentityCapabilityImplementation(),))
    composition = RecordingComposition(resolver)
    planner = RecordingPlanner()
    context_factory = RecordingContextFactory(iter((FIRST_EXECUTION_ID,)))
    engines: list[RecordingEngine] = []

    def engine_factory(actual_resolver: CapabilityResolver) -> ExecutionEngine:
        engine = RecordingEngine(actual_resolver)
        engines.append(engine)
        return engine

    result = RuntimeHost(
        tmp_path,
        selector,
        composition,
        planner=planner,
        context_factory=context_factory,
        engine_factory=engine_factory,
    ).execute(event)

    assert len(composition.calls) == 1
    assert composition.calls[0][0] is event
    assert composition.calls[0][1].workflow_id == "identity"
    assert len(planner.calls) == 1
    assert len(context_factory.calls) == 1
    assert context_factory.calls[0][1] == {"value": "unchanged"}
    assert len(engines) == 1
    assert len(engines[0].calls) == 1
    assert result.execution_id == FIRST_EXECUTION_ID
    assert result.workflow_id == "identity"
    assert result.workflow_version == "7"
    assert result.success is True
    assert result.final_artifact.name == "result"
    assert result.final_artifact.payload == "unchanged"


def test_runtime_host_creates_a_fresh_context_for_each_event(tmp_path: Path) -> None:
    write_project(tmp_path)
    selector = InMemoryWorkflowSelector(
        {"command": WorkflowRoute(workflow_id="identity", workflow_version="7")}
    )
    composition = RecordingComposition(
        InMemoryCapabilityResolver((IdentityCapabilityImplementation(),))
    )
    host = RuntimeHost(
        tmp_path,
        selector,
        composition,
        context_factory=RecordingContextFactory(
            iter((FIRST_EXECUTION_ID, SECOND_EXECUTION_ID))
        ),
    )

    first = host.execute(HostEvent(event_kind="command", inputs={"value": "first"}))
    second = host.execute(HostEvent(event_kind="command", inputs={"value": "second"}))

    assert first.execution_id == FIRST_EXECUTION_ID
    assert second.execution_id == SECOND_EXECUTION_ID
    assert first.final_artifact.payload == "first"
    assert second.final_artifact.payload == "second"


def test_invalid_host_inputs_prevent_composition_and_engine_execution(
    tmp_path: Path,
) -> None:
    write_project(tmp_path)
    selector = InMemoryWorkflowSelector(
        {"command": WorkflowRoute(workflow_id="identity", workflow_version="7")}
    )
    composition = RecordingComposition(
        InMemoryCapabilityResolver((IdentityCapabilityImplementation(),))
    )
    engine_calls = 0

    def engine_factory(resolver: CapabilityResolver) -> ExecutionEngine:
        nonlocal engine_calls
        engine_calls += 1
        return ExecutionEngine(resolver)

    host = RuntimeHost(
        tmp_path,
        selector,
        composition,
        engine_factory=engine_factory,
    )

    with pytest.raises(
        InvalidWorkflowInputType,
        match="'value'.*'string'.*'integer'",
    ):
        host.execute(HostEvent(event_kind="command", inputs={"value": 42}))

    assert composition.calls == []
    assert engine_calls == 0

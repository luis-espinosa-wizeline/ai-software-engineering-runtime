import pytest

from app.shared import JsonValue, Metadata
from app.workflows import (
    AmbiguousActiveWorkflow,
    DuplicateWorkflow,
    InMemoryWorkflowDiscovery,
    InvalidWorkflowDefinition,
    WorkflowDefinition,
    WorkflowNotFound,
    WorkflowRegistry,
    WorkflowStepDefinition,
)


def workflow(
    workflow_id: str,
    version: str,
    *,
    active: bool = False,
    enabled: bool = True,
    triggers: list[str] | None = None,
) -> WorkflowDefinition:
    trigger_metadata: list[JsonValue] = list(triggers or [])
    metadata: Metadata = {
        "active": active,
        "enabled": enabled,
        "triggers": trigger_metadata,
    }
    return WorkflowDefinition(
        workflow_id=workflow_id,
        name=f"{workflow_id} {version}",
        version=version,
        steps=(WorkflowStepDefinition(step_id="first", name="First"),),
        metadata=metadata,
    )


def test_in_memory_discovery_snapshots_and_exposes_definitions() -> None:
    definitions = [workflow("review", "1", active=True)]
    discovery = InMemoryWorkflowDiscovery(definitions)

    definitions.append(workflow("release", "1"))

    assert discovery.discover() == (definitions[0],)
    assert isinstance(discovery.discover(), tuple)


def test_registry_can_be_created_from_discovery_and_can_be_empty() -> None:
    definition = workflow("review", "1", active=True)

    registry = WorkflowRegistry.from_discovery(InMemoryWorkflowDiscovery((definition,)))

    assert registry.list() == (definition,)
    assert WorkflowRegistry(()).list() == ()


def test_registry_rejects_duplicate_workflow_identity() -> None:
    duplicate = workflow("review", "1")

    with pytest.raises(DuplicateWorkflow, match="'review'.*'1'"):
        WorkflowRegistry((duplicate, duplicate))


def test_registry_rejects_multiple_active_versions() -> None:
    with pytest.raises(AmbiguousActiveWorkflow, match="multiple active versions"):
        WorkflowRegistry(
            (
                workflow("review", "1", active=True),
                workflow("review", "2", active=True),
            )
        )


def test_registry_resolves_specific_and_active_versions() -> None:
    old = workflow("review", "v-old")
    current = workflow("review", "v-current", active=True)
    registry = WorkflowRegistry((old, current))

    assert registry.get("review", "v-old") is old
    assert registry.get("review") is current
    assert registry.active_version("review") == "v-current"
    assert registry.exists("review")
    assert not registry.exists("unknown")


def test_unknown_workflow_and_version_raise_workflow_not_found() -> None:
    registry = WorkflowRegistry((workflow("review", "1"),))

    with pytest.raises(WorkflowNotFound, match="not registered"):
        registry.get("unknown")
    with pytest.raises(WorkflowNotFound, match="version '2'"):
        registry.get("review", "2")
    with pytest.raises(WorkflowNotFound, match="no active version"):
        registry.active_version("review")


def test_registry_filters_enabled_workflows() -> None:
    enabled = workflow("enabled", "1")
    disabled = workflow("disabled", "1", enabled=False)
    implicit = WorkflowDefinition(workflow_id="implicit", name="Implicit", version="1")
    registry = WorkflowRegistry((enabled, disabled, implicit))

    assert registry.list_enabled() == (enabled, implicit)


def test_registry_filters_workflows_by_trigger() -> None:
    manual = workflow("manual", "1", triggers=["manual"])
    both = workflow("both", "1", triggers=["schedule", "manual"])
    registry = WorkflowRegistry((manual, both))

    assert registry.list_by_trigger("manual") == (both, manual)
    assert registry.list_by_trigger("schedule") == (both,)
    assert registry.list_by_trigger("unknown") == ()


def test_registry_order_is_deterministic_and_versions_are_opaque() -> None:
    definitions = (
        workflow("zeta", "1"),
        workflow("alpha", "10"),
        workflow("alpha", "2"),
    )

    ordered = WorkflowRegistry(reversed(definitions)).list()

    assert tuple((item.workflow_id, item.version) for item in ordered) == (
        ("alpha", "10"),
        ("alpha", "2"),
        ("zeta", "1"),
    )


def test_registry_exposes_immutable_collections_and_is_immutable() -> None:
    definition = workflow("review", "1")
    registry = WorkflowRegistry((definition,))

    listed = registry.list()

    assert isinstance(listed, tuple)
    with pytest.raises(TypeError):
        listed[0] = definition  # type: ignore[index]
    with pytest.raises(AttributeError, match="immutable"):
        registry.extra = "value"


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"active": "yes"}, "active.*boolean"),
        ({"active": None}, "active.*boolean"),
        ({"enabled": 1}, "enabled.*boolean"),
        ({"triggers": "manual"}, "triggers.*list"),
        ({"triggers": None}, "triggers.*list"),
        ({"triggers": [""]}, "triggers.*list"),
    ],
)
def test_registry_rejects_invalid_registry_metadata(
    metadata: Metadata, message: str
) -> None:
    definition = WorkflowDefinition(
        workflow_id="review",
        name="Review",
        version="1",
        metadata=metadata,
    )

    with pytest.raises(InvalidWorkflowDefinition, match=message):
        WorkflowRegistry((definition,))

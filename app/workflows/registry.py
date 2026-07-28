"""Validated, immutable workflow definition catalog."""

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

from app.workflows.discovery import WorkflowDiscovery
from app.workflows.errors import (
    AmbiguousActiveWorkflow,
    DuplicateWorkflow,
    InvalidWorkflowDefinition,
    WorkflowNotFound,
)
from app.workflows.models import WorkflowDefinition

ACTIVE_METADATA_KEY: Final = "active"
ENABLED_METADATA_KEY: Final = "enabled"
TRIGGERS_METADATA_KEY: Final = "triggers"

type WorkflowKey = tuple[str, str]


class WorkflowRegistry:
    """An immutable, deterministic catalog of validated workflow definitions."""

    __slots__ = ("_active", "_by_key", "_workflows")

    _active: Mapping[str, WorkflowDefinition]
    _by_key: Mapping[WorkflowKey, WorkflowDefinition]
    _workflows: tuple[WorkflowDefinition, ...]

    def __init__(self, workflows: Iterable[WorkflowDefinition]) -> None:
        ordered = tuple(
            sorted(workflows, key=lambda workflow: (workflow.workflow_id, workflow.version))
        )
        by_key: dict[WorkflowKey, WorkflowDefinition] = {}
        active: dict[str, WorkflowDefinition] = {}

        for workflow in ordered:
            self._validate_metadata(workflow)
            key = (workflow.workflow_id, workflow.version)
            if key in by_key:
                raise DuplicateWorkflow(
                    f"Workflow {workflow.workflow_id!r} version {workflow.version!r} "
                    "is registered more than once."
                )
            by_key[key] = workflow

            if self._is_active(workflow):
                if workflow.workflow_id in active:
                    raise AmbiguousActiveWorkflow(
                        f"Workflow {workflow.workflow_id!r} has multiple active versions."
                    )
                active[workflow.workflow_id] = workflow

        object.__setattr__(self, "_workflows", ordered)
        object.__setattr__(self, "_by_key", MappingProxyType(by_key))
        object.__setattr__(self, "_active", MappingProxyType(active))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    @classmethod
    def from_discovery(cls, discovery: WorkflowDiscovery) -> WorkflowRegistry:
        """Build a validated registry from a discovery source."""
        return cls(discovery.discover())

    def get(self, workflow_id: str, version: str | None = None) -> WorkflowDefinition:
        """Return a version, or the explicitly active version when omitted."""
        if version is None:
            return self._get_active(workflow_id)
        try:
            return self._by_key[(workflow_id, version)]
        except KeyError as error:
            raise WorkflowNotFound(
                f"Workflow {workflow_id!r} version {version!r} is not registered."
            ) from error

    def exists(self, workflow_id: str) -> bool:
        """Return whether any version of a workflow id is registered."""
        return any(key[0] == workflow_id for key in self._by_key)

    def list(self) -> tuple[WorkflowDefinition, ...]:
        """Return all definitions in workflow-id then version order."""
        return self._workflows

    def list_enabled(self) -> tuple[WorkflowDefinition, ...]:
        """Return definitions that are enabled by registry metadata."""
        return tuple(workflow for workflow in self._workflows if self._is_enabled(workflow))

    def list_by_trigger(self, trigger: str) -> tuple[WorkflowDefinition, ...]:
        """Return definitions declaring support for the supplied trigger."""
        return tuple(
            workflow for workflow in self._workflows if trigger in self._triggers(workflow)
        )

    def active_version(self, workflow_id: str) -> str:
        """Return the opaque version string explicitly active for a workflow id."""
        return self._get_active(workflow_id).version

    def _get_active(self, workflow_id: str) -> WorkflowDefinition:
        try:
            return self._active[workflow_id]
        except KeyError as error:
            if self.exists(workflow_id):
                message = f"Workflow {workflow_id!r} has no active version."
            else:
                message = f"Workflow {workflow_id!r} is not registered."
            raise WorkflowNotFound(message) from error

    @staticmethod
    def _is_active(workflow: WorkflowDefinition) -> bool:
        return workflow.metadata.get(ACTIVE_METADATA_KEY, False) is True

    @staticmethod
    def _is_enabled(workflow: WorkflowDefinition) -> bool:
        return workflow.metadata.get(ENABLED_METADATA_KEY, True) is True

    @staticmethod
    def _triggers(workflow: WorkflowDefinition) -> tuple[str, ...]:
        value = workflow.metadata.get(TRIGGERS_METADATA_KEY, [])
        if not isinstance(value, list):
            return ()
        return tuple(trigger for trigger in value if isinstance(trigger, str))

    @staticmethod
    def _validate_metadata(workflow: WorkflowDefinition) -> None:
        for key in (ACTIVE_METADATA_KEY, ENABLED_METADATA_KEY):
            value = workflow.metadata.get(key)
            if key in workflow.metadata and not isinstance(value, bool):
                raise InvalidWorkflowDefinition(
                    f"Workflow {workflow.workflow_id!r} version {workflow.version!r} "
                    f"metadata {key!r} must be a boolean."
                )

        triggers = workflow.metadata.get(TRIGGERS_METADATA_KEY)
        if TRIGGERS_METADATA_KEY in workflow.metadata and (
            not isinstance(triggers, list)
            or any(not isinstance(trigger, str) or not trigger for trigger in triggers)
        ):
            raise InvalidWorkflowDefinition(
                f"Workflow {workflow.workflow_id!r} version {workflow.version!r} "
                f"metadata {TRIGGERS_METADATA_KEY!r} must be a list of non-empty strings."
            )

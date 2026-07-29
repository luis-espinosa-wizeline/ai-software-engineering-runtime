"""Coordination of project configuration and resource discovery."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.project.errors import (
    InvalidProjectConfiguration,
    ProjectConfigurationNotFound,
)
from app.project.models import Project
from app.project.yaml import load_yaml_mapping, require_exact_fields

if TYPE_CHECKING:
    from app.capabilities.loader import CapabilityLoader
    from app.workflows.loader import WorkflowLoader


class ProjectLoader:
    """Load a project configuration and its discoverable resources."""

    def __init__(
        self,
        workflow_loader: WorkflowLoader | None = None,
        capability_loader: CapabilityLoader | None = None,
    ) -> None:
        if workflow_loader is None:
            from app.workflows.loader import WorkflowLoader

            workflow_loader = WorkflowLoader()
        if capability_loader is None:
            from app.capabilities.loader import CapabilityLoader

            capability_loader = CapabilityLoader()
        self._workflow_loader = workflow_loader
        self._capability_loader = capability_loader

    def load(self, project_root: str | Path) -> Project:
        """Construct an immutable snapshot of a project directory."""
        root = Path(project_root)
        config_path = root / "runtime.yaml"
        if not config_path.is_file():
            raise ProjectConfigurationNotFound(config_path)

        data, parse_error = load_yaml_mapping(config_path)
        if parse_error is not None:
            raise InvalidProjectConfiguration(config_path, parse_error)
        assert data is not None
        self._validate_configuration(config_path, data)

        return Project(
            name=data["name"],
            version=data["version"],
            workflows=self._workflow_loader.load(root / "workflows"),
            capabilities=self._capability_loader.load(root / "app" / "capabilities"),
        )

    @staticmethod
    def _validate_configuration(path: Path, data: dict[str, Any]) -> None:
        field_error = require_exact_fields(data, required={"name", "version"})
        if field_error is not None:
            raise InvalidProjectConfiguration(path, field_error)
        if not isinstance(data["name"], str) or not data["name"].strip():
            raise InvalidProjectConfiguration(path, "name must be a non-empty string")
        if (
            not isinstance(data["version"], int)
            or isinstance(data["version"], bool)
            or data["version"] < 1
        ):
            raise InvalidProjectConfiguration(path, "version must be a positive integer")

"""Errors raised while discovering project resources."""

from pathlib import Path


class ProjectDiscoveryError(Exception):
    """Base error for project discovery failures."""


class ProjectConfigurationNotFound(ProjectDiscoveryError):
    """Raised when a project does not contain runtime.yaml."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Project configuration not found: {path}")


class InvalidProjectConfiguration(ProjectDiscoveryError):
    """Raised when runtime.yaml is malformed."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"Invalid project configuration {path}: {detail}")


class InvalidWorkflowDefinitionFile(ProjectDiscoveryError):
    """Raised when a workflow YAML file is malformed."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"Invalid workflow definition {path}: {detail}")


class InvalidCapabilityManifest(ProjectDiscoveryError):
    """Raised when a capability manifest is malformed."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"Invalid capability manifest {path}: {detail}")


class DuplicateWorkflowName(ProjectDiscoveryError):
    """Raised when two discovered workflows have the same name."""

    def __init__(self, name: str, first: Path, duplicate: Path) -> None:
        super().__init__(
            f"Duplicate workflow name {name!r} in {first} and {duplicate}"
        )


class DuplicateCapabilityName(ProjectDiscoveryError):
    """Raised when two discovered capability manifests have the same name."""

    def __init__(self, name: str, first: Path, duplicate: Path) -> None:
        super().__init__(
            f"Duplicate capability name {name!r} in {first} and {duplicate}"
        )

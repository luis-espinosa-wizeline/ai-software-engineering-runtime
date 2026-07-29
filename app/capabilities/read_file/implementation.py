"""Local-filesystem implementation of the provider-neutral ReadFile Capability."""

from collections.abc import Callable
from pathlib import Path

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)

READ_FILE = Capability(
    name="ReadFile",
    description="Read the UTF-8 text content of a file.",
    category=CapabilityCategory.REPOSITORY,
    contract="ReadFile",
    version="1",
    input_artifacts=(
        ArtifactDefinition(name="path", description="Path of the file to read."),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="SourceCode", description="Source path and UTF-8 text content."
        ),
    ),
    tags=("repository", "file", "read"),
)


class ReadFileImplementation:
    """Read UTF-8 text using a replaceable implementation-local file reader."""

    def __init__(self, read_text: Callable[[Path], str] | None = None) -> None:
        self._read_text = read_text or self._read_utf8

    @property
    def capability(self) -> Capability:
        return READ_FILE

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        path_value = request.artifact("path").payload
        if not isinstance(path_value, str) or not path_value:
            raise ValueError("path artifact must contain a non-empty string")

        path = Path(path_value)
        content = self._read_text(path)
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="SourceCode",
                    payload={"path": str(path), "content": content},
                ),
            )
        )

    @staticmethod
    def _read_utf8(path: Path) -> str:
        return path.read_text(encoding="utf-8")

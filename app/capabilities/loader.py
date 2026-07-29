"""Filesystem discovery of capability manifests."""

from pathlib import Path
from typing import Any

from app.capabilities.models import ArtifactDefinition
from app.project.errors import DuplicateCapabilityName, InvalidCapabilityManifest
from app.project.models import CapabilityDescriptor
from app.project.yaml import load_yaml_mapping, require_exact_fields


class CapabilityLoader:
    """Discover immediate capability packages without importing their entrypoints."""

    def load(self, capabilities_directory: str | Path) -> tuple[CapabilityDescriptor, ...]:
        """Load descriptors from immediate directories containing manifest.yaml."""
        directory = Path(capabilities_directory)
        if not directory.is_dir():
            return ()

        discovered: list[tuple[CapabilityDescriptor, Path]] = []
        by_name: dict[str, Path] = {}
        for package in sorted(directory.iterdir(), key=lambda path: path.name):
            if (
                not package.is_dir()
                or package.name.startswith(".")
                or package.name == "__pycache__"
            ):
                continue
            manifest = package / "manifest.yaml"
            if not manifest.is_file():
                continue
            descriptor = self._load_manifest(manifest)
            previous = by_name.get(descriptor.name)
            if previous is not None:
                raise DuplicateCapabilityName(descriptor.name, previous, manifest)
            by_name[descriptor.name] = manifest
            discovered.append((descriptor, manifest))

        return tuple(
            descriptor
            for descriptor, _ in sorted(discovered, key=lambda item: item[0].name)
        )

    @staticmethod
    def _load_manifest(path: Path) -> CapabilityDescriptor:
        data, parse_error = load_yaml_mapping(path)
        if parse_error is not None:
            raise InvalidCapabilityManifest(path, parse_error)
        assert data is not None
        field_error = require_exact_fields(
            data,
            required={
                "name",
                "description",
                "category",
                "contract",
                "version",
                "inputs",
                "outputs",
                "tags",
                "entrypoint",
            },
        )
        if field_error is not None:
            raise InvalidCapabilityManifest(path, field_error)
        for field in (
            "name",
            "description",
            "category",
            "contract",
            "version",
            "entrypoint",
        ):
            value: Any = data[field]
            if not isinstance(value, str) or not value.strip():
                raise InvalidCapabilityManifest(
                    path, f"{field} must be a non-empty string"
                )
        try:
            return CapabilityDescriptor(
                name=data["name"],
                description=data["description"],
                category=data["category"],
                contract=data["contract"],
                version=data["version"],
                input_artifacts=CapabilityLoader._artifact_definitions(
                    path, data["inputs"], "inputs"
                ),
                output_artifacts=CapabilityLoader._artifact_definitions(
                    path, data["outputs"], "outputs"
                ),
                tags=CapabilityLoader._tags(path, data["tags"]),
                entrypoint=data["entrypoint"],
            )
        except ValueError as error:
            raise InvalidCapabilityManifest(path, str(error)) from error

    @staticmethod
    def _artifact_definitions(
        path: Path, value: Any, field: str
    ) -> tuple[ArtifactDefinition, ...]:
        if not isinstance(value, list):
            raise InvalidCapabilityManifest(path, f"{field} must be a list")
        definitions: list[ArtifactDefinition] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict) or set(item) != {"name", "description"}:
                raise InvalidCapabilityManifest(
                    path,
                    f"{field}[{index}] must contain exactly name and description",
                )
            if not all(
                isinstance(item[key], str) and item[key].strip()
                for key in ("name", "description")
            ):
                raise InvalidCapabilityManifest(
                    path, f"{field}[{index}] values must be non-empty strings"
                )
            definitions.append(
                ArtifactDefinition(
                    name=item["name"], description=item["description"]
                )
            )
        return tuple(definitions)

    @staticmethod
    def _tags(path: Path, value: Any) -> tuple[str, ...]:
        if not isinstance(value, list) or not all(
            isinstance(tag, str) and tag.strip() for tag in value
        ):
            raise InvalidCapabilityManifest(
                path, "tags must be a list of non-empty strings"
            )
        return tuple(value)

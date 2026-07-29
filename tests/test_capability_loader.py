from pathlib import Path

import pytest
from pydantic import ValidationError

from app.capabilities import CapabilityLoader
from app.project import DuplicateCapabilityName, InvalidCapabilityManifest


def manifest(root: Path, package: str, content: str) -> None:
    directory = root / package
    directory.mkdir(parents=True)
    (directory / "manifest.yaml").write_text(content, encoding="utf-8")


def valid_manifest(name: str, contract: str, entrypoint: str) -> str:
    return f"""
name: {name}
description: Test capability.
category: repository
contract: {contract}
version: "1"
inputs: []
outputs:
  - name: result
    description: Test result.
tags: [test]
entrypoint: {entrypoint}
"""


def test_capability_loader_maps_manifests_and_orders_by_name(tmp_path: Path) -> None:
    manifest(
        tmp_path,
        "z_package",
        valid_manifest("analyze", "Analyze", "example.analyze"),
    )
    manifest(
        tmp_path,
        "a_package",
        valid_manifest("read", "Read", "example.read"),
    )

    descriptors = CapabilityLoader().load(tmp_path)

    assert tuple(item.name for item in descriptors) == ("analyze", "read")
    assert descriptors[1].contract == "Read"
    assert descriptors[1].entrypoint == "example.read"
    assert descriptors[1].category == "repository"
    assert descriptors[1].output_artifacts[0].name == "result"
    with pytest.raises(ValidationError):
        descriptors[0].name = "changed"


def test_capability_loader_ignores_non_packages_and_directories_without_manifest(
    tmp_path: Path,
) -> None:
    manifest(
        tmp_path,
        "valid",
        valid_manifest("valid", "Valid", "example.valid"),
    )
    (tmp_path / "support").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    assert tuple(item.name for item in CapabilityLoader().load(tmp_path)) == ("valid",)


@pytest.mark.parametrize(
    "content",
    [
        "name: broken\ncontract: Broken\n",
        "name: broken\ncontract: []\nentrypoint: example.broken\n",
        "name: broken\ncontract: Broken\nentrypoint: example\nextra: value\n",
        "name: [\n",
    ],
)
def test_capability_loader_reports_malformed_manifests(
    tmp_path: Path, content: str
) -> None:
    manifest(tmp_path, "broken", content)

    with pytest.raises(InvalidCapabilityManifest, match="manifest.yaml"):
        CapabilityLoader().load(tmp_path)


def test_capability_loader_rejects_duplicate_names(tmp_path: Path) -> None:
    content = valid_manifest("duplicate", "Contract", "example.value")
    manifest(tmp_path, "first", content)
    manifest(tmp_path, "second", content)

    with pytest.raises(DuplicateCapabilityName, match="duplicate"):
        CapabilityLoader().load(tmp_path)


def test_capability_loader_does_not_import_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest(
        tmp_path,
        "dangerous",
        valid_manifest("safe", "Safe", "does.not.exist"),
    )

    def fail_import(name: str, package: str | None = None) -> None:
        raise AssertionError(f"unexpected import: {name}, {package}")

    monkeypatch.setattr("importlib.import_module", fail_import)

    assert CapabilityLoader().load(tmp_path)[0].entrypoint == "does.not.exist"

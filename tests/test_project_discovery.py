from pathlib import Path

import pytest
from pydantic import ValidationError

from app.project import (
    InvalidProjectConfiguration,
    ProjectConfigurationNotFound,
    ProjectLoader,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_project_loader_constructs_an_immutable_project(tmp_path: Path) -> None:
    write(
        tmp_path / "runtime.yaml",
        "name: AI Software Engineering Runtime\nversion: 1\n",
    )
    write(
        tmp_path / "workflows" / "review.yaml",
        """
name: review
description: Review a source file.
inputs:
  file_path:
    type: string
steps:
  - id: read
    action: ReadFile
    inputs:
      path:
        workflow_input: file_path
    outputs: [source]
result:
  step: read
  artifact: source
""",
    )
    write(
        tmp_path / "app" / "capabilities" / "read_file" / "manifest.yaml",
        """
name: read_file
description: Read a file.
category: repository
contract: ReadFile
version: "1"
inputs:
  - name: path
    description: File path.
outputs:
  - name: file
    description: File contents.
tags: [repository, read]
entrypoint: app.capabilities.read_file.implementation
""",
    )

    project = ProjectLoader().load(tmp_path)

    assert project.name == "AI Software Engineering Runtime"
    assert project.version == 1
    assert tuple(item.name for item in project.workflows) == ("review",)
    assert tuple(item.name for item in project.capabilities) == ("read_file",)
    with pytest.raises(ValidationError):
        project.name = "changed"


def test_project_loader_supports_absent_resource_directories(tmp_path: Path) -> None:
    write(tmp_path / "runtime.yaml", "name: Empty project\nversion: 1\n")

    project = ProjectLoader().load(tmp_path)

    assert project.workflows == ()
    assert project.capabilities == ()


def test_project_loader_reports_missing_configuration(tmp_path: Path) -> None:
    with pytest.raises(ProjectConfigurationNotFound, match="runtime.yaml"):
        ProjectLoader().load(tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        "name: Missing version\n",
        "name: Invalid version\nversion: one\n",
        "name: [not, a, string]\nversion: 1\n",
        "name: Invalid YAML\nversion: [\n",
        "name: Extra\nversion: 1\nproviders: {}\n",
    ],
)
def test_project_loader_reports_malformed_configuration(
    tmp_path: Path, content: str
) -> None:
    write(tmp_path / "runtime.yaml", content)

    with pytest.raises(InvalidProjectConfiguration, match="runtime.yaml"):
        ProjectLoader().load(tmp_path)

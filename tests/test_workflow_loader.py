from pathlib import Path

import pytest

from app.project import DuplicateWorkflowName, InvalidWorkflowDefinitionFile
from app.workflows import (
    WorkflowInputDefinition,
    WorkflowInputReference,
    WorkflowInputType,
    WorkflowLoader,
    WorkflowStepOutputReference,
)

VALID_WORKFLOW = """
name: review
version: "2"
description: Review source.
inputs:
  file_path:
    type: string
steps:
  - id: read_source
    name: Read source
    action: ReadFile
    inputs:
      path:
        workflow_input: file_path
    outputs:
      - source
  - id: analyze
    action: AnalyzeSource
    inputs:
      source:
        step_output:
          step: read_source
          artifact: source
    outputs: [findings]
result:
  step: analyze
  artifact: findings
"""


def workflow_file(root: Path, name: str, content: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(content, encoding="utf-8")


def test_workflow_loader_maps_to_existing_domain_model(tmp_path: Path) -> None:
    workflow_file(tmp_path, "review.yaml", VALID_WORKFLOW)

    workflow = WorkflowLoader().load(tmp_path)[0]

    assert workflow.workflow_id == "review"
    assert workflow.name == "review"
    assert workflow.version == "2"
    assert workflow.inputs == (
        WorkflowInputDefinition(
            name="file_path",
            type=WorkflowInputType.STRING,
            required=True,
        ),
    )
    assert workflow.required_inputs == ("file_path",)
    assert isinstance(workflow.steps[0].input_bindings[0].source, WorkflowInputReference)
    assert isinstance(
        workflow.steps[1].input_bindings[0].source, WorkflowStepOutputReference
    )
    assert workflow.steps[1].outputs == ("findings",)
    assert workflow.result is not None
    assert workflow.result.output_name == "findings"


def test_workflow_loader_discovers_multiple_files_in_name_order(tmp_path: Path) -> None:
    workflow_file(tmp_path, "first-file.yaml", VALID_WORKFLOW.replace("review", "zeta", 1))
    workflow_file(tmp_path, "second-file.yaml", VALID_WORKFLOW.replace("review", "alpha", 1))
    workflow_file(tmp_path, "ignored.yml", VALID_WORKFLOW)
    workflow_file(tmp_path, "notes.txt", "ignored")

    assert tuple(item.name for item in WorkflowLoader().load(tmp_path)) == (
        "alpha",
        "zeta",
    )


@pytest.mark.parametrize(
    "content",
    [
        "name: broken\n",
        VALID_WORKFLOW.replace("type: string", "type: unsupported"),
        VALID_WORKFLOW.replace("type: string", "required: true"),
        VALID_WORKFLOW.replace("type: string", 'type: string\n    required: "true"'),
        VALID_WORKFLOW.replace("type: string", "type: string\n    unknown: value"),
        VALID_WORKFLOW.replace("outputs:\n      - source", "outputs: source"),
        VALID_WORKFLOW.replace("workflow_input: file_path", "literal: value"),
        VALID_WORKFLOW + "\nunknown: value\n",
        "name: [\n",
    ],
)
def test_workflow_loader_reports_malformed_definitions(
    tmp_path: Path, content: str
) -> None:
    workflow_file(tmp_path, "broken.yaml", content)

    with pytest.raises(InvalidWorkflowDefinitionFile, match="broken.yaml"):
        WorkflowLoader().load(tmp_path)


def test_workflow_loader_rejects_duplicate_names(tmp_path: Path) -> None:
    workflow_file(tmp_path, "one.yaml", VALID_WORKFLOW)
    workflow_file(tmp_path, "two.yaml", VALID_WORKFLOW.replace('version: "2"', 'version: "3"'))

    with pytest.raises(DuplicateWorkflowName, match="review"):
        WorkflowLoader().load(tmp_path)


def test_workflow_version_defaults_to_one(tmp_path: Path) -> None:
    workflow_file(tmp_path, "review.yaml", VALID_WORKFLOW.replace('version: "2"\n', ""))

    assert WorkflowLoader().load(tmp_path)[0].version == "1"


def test_workflow_loader_supports_all_structural_input_types(tmp_path: Path) -> None:
    declarations = "\n".join(
        f"  {input_type.value}_value:\n"
        f"    type: {input_type.value}\n"
        "    required: false"
        for input_type in WorkflowInputType
    )
    workflow_file(
        tmp_path,
        "types.yaml",
        f"""
name: types
inputs:
{declarations}
steps:
  - id: result
    action: Result
    inputs: {{}}
    outputs: [result]
result:
  step: result
  artifact: result
""",
    )

    workflow = WorkflowLoader().load(tmp_path)[0]

    assert tuple(definition.type for definition in workflow.inputs) == tuple(
        WorkflowInputType
    )
    assert all(definition.required is False for definition in workflow.inputs)


def test_workflow_loader_rejects_duplicate_input_definitions(tmp_path: Path) -> None:
    workflow_file(
        tmp_path,
        "duplicate.yaml",
        VALID_WORKFLOW.replace(
            "  file_path:\n    type: string",
            "  file_path:\n    type: string\n  file_path:\n    type: integer",
        ),
    )

    with pytest.raises(
        InvalidWorkflowDefinitionFile,
        match="duplicate.yaml.*duplicate field: file_path",
    ):
        WorkflowLoader().load(tmp_path)


def test_workflow_loader_maps_iteration_pattern(tmp_path: Path) -> None:
    workflow_file(
        tmp_path,
        "iterate.yaml",
        """
name: iterate
inputs:
  items:
    type: string
steps:
  - id: transform
    action: Transform
    inputs:
      item:
        workflow_input: items
    outputs: [result]
    iteration:
      input: item
result:
  step: transform
  artifact: result
""",
    )

    workflow = WorkflowLoader().load(tmp_path)[0]

    assert workflow.steps[0].iteration is not None
    assert workflow.steps[0].iteration.input_parameter == "item"

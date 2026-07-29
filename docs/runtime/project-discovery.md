# Project Discovery

Project discovery turns a project directory into an immutable in-memory
`Project`. A project contains only its name, version, discovered
`WorkflowDefinition` values, and discovered `CapabilityDescriptor` values.
It contains no filesystem behavior, executable capabilities, resolver, planner,
or runtime state.

```text
Project directory
        |
        v
ProjectLoader
        |-- WorkflowLoader
        `-- CapabilityLoader
        |
        v
Project
        |-- WorkflowDefinitions
        `-- CapabilityDescriptors
```

`ProjectLoader.load(path)` requires `runtime.yaml`, then delegates direct
workflow-file discovery to `WorkflowLoader` and immediate capability-package
discovery to `CapabilityLoader`. Missing `workflows/` and
`app/capabilities/` directories are treated as empty collections.

Discovery produces an in-memory Project. Planning and execution remain separate
downstream concerns.

## Supported project layout

```text
runtime.yaml
workflows/
    review.yaml
app/
    capabilities/
        read_file/
            __init__.py
            manifest.yaml
            implementation.py
```

Only `.yaml` workflow files directly under `workflows/` are discovered. Files
with a `.yml` extension and unrelated files are ignored. Only immediate
subdirectories of `app/capabilities/` containing `manifest.yaml` are
discoverable. Hidden directories, `__pycache__`, files, and directories without
a manifest are ignored. Both resource collections are returned in ascending
resource-name order. Duplicate names are errors and identify both affected
files.

## Project configuration

`runtime.yaml` has exactly two fields:

```yaml
name: AI Software Engineering Runtime
version: 1
```

`name` is a non-empty string. `version` is a positive integer. Unknown or missing
fields are rejected.

## Capability discovery

A capability owns its package and manifest:

```text
app/capabilities/read_file/
    __init__.py
    manifest.yaml
    implementation.py
```

The manifest contains the Capability's public metadata plus its opaque
entrypoint:

```yaml
name: ReadFile
description: Read the UTF-8 text content of a file.
category: repository
contract: ReadFile
version: "1"
inputs:
  - name: path
    description: Path of the file to read.
outputs:
  - name: SourceCode
    description: Source path and UTF-8 text content.
tags:
  - repository
  - file
  - read
entrypoint: app.capabilities.read_file.implementation
```

`CapabilityLoader` maps this metadata to an immutable
`CapabilityDescriptor`. The entrypoint remains an opaque string. Discovery does
not import it, inspect Python classes, instantiate a `CapabilityImplementation`,
or register anything with `CapabilityResolver`. See
[Capability Metadata and Catalog](capability-catalog.md) for field validation
and the initial public catalog.

## Workflow discovery

Workflow YAML maps explicitly to the existing workflow domain:

- `name` maps to both `WorkflowDefinition.workflow_id` and
  `WorkflowDefinition.name`;
- optional `version` maps to `WorkflowDefinition.version` and defaults to
  `"1"`;
- optional `description` maps directly;
- each key under `inputs` becomes an immutable `WorkflowInputDefinition`
  retaining its name, structural type, and required flag;
- step `id`, `action`, and `outputs` map to `step_id`, `action_contract`, and
  `outputs`;
- step input bindings become `WorkflowInputReference` or
  `WorkflowStepOutputReference`;
- result `step` and `artifact` become a `WorkflowResultReference`.

The supported schema is:

```yaml
name: review
version: "1" # optional; defaults to "1"
description: Review a source file and produce a Markdown report. # optional

inputs:
  file_path:
    type: string
    required: true # optional; defaults to true

steps:
  - id: read_source
    name: Read source # optional; defaults to id
    description: Load the requested source file. # optional
    action: ReadFile
    inputs:
      path:
        workflow_input: file_path
    outputs:
      - source
    # Optional for a list-valued binding:
    # iteration:
    #   input: path

  - id: generate_report
    action: GenerateMarkdown
    inputs:
      source:
        step_output:
          step: read_source
          artifact: source
    outputs:
      - report

result:
  step: generate_report
  artifact: report
```

`name`, `inputs`, `steps`, and `result` are required. Workflow inputs support
`string`, `integer`, `boolean`, `number`, `object`, and `array`. The `required`
field must be a boolean and defaults to `true`. Step `id`, `action`, `inputs`,
and `outputs` are required. Optional `iteration.input` must name one of the
step's input parameters, and an iterated step must declare outputs. Bindings
contain exactly one of `workflow_input` or `step_output`; a `step_output`
contains exactly `step` and `artifact`. The result contains exactly `step` and
`artifact`. Unknown fields, duplicate mapping keys, unsupported types, and
malformed values are rejected with an error identifying the file.

Loading performs structural parsing only. It does not validate whether actions
have installed capabilities, validate reference semantics, plan, or execute the
workflow.

Host-side invocation validation is documented in
[Workflow Input Contracts](workflow-input-contracts.md).

## Runtime evolution principles

Project discovery follows these constraints:

1. Establish a domain responsibility before introducing its implementation.
2. Add abstractions only when a current use case earns them.
3. Add complexity only for current requirements.
4. Preserve stable Core Runtime behavior and make only necessary compatibility
   changes.
5. Drive future evolution through concrete capabilities and workflows.
6. Leave compatible, working implementations unchanged.

Accordingly, this foundation contains no capability registry, factory, plugin
framework, dynamic import, dependency management, provider resolution, caching,
persistence, planning, or execution.

# Capability Metadata and Catalog

Capabilities are the public engineering API of the Runtime. A Capability
describes a reusable transformation without exposing its implementation or any
infrastructure it may use. Metadata makes that transformation understandable
and composable without reading Python source.

## Metadata model

Every `Capability` and discovered `CapabilityDescriptor` exposes:

- `name`: stable human-readable identity;
- `description`: concise purpose;
- `category`: one of `repository`, `analysis`, `transformation`, or
  `publishing`;
- `contract`: provider-neutral Action Contract used by workflow plans;
- `version`: opaque, non-empty Capability version;
- `input_artifacts`: ordered artifact names and descriptions;
- `output_artifacts`: one or more ordered artifact names and descriptions; and
- `tags`: unique discovery terms.

`ArtifactDefinition` describes only the name and meaning of a boundary artifact.
It does not introduce a schema language, serializer, provider type, or execution
behavior. Metadata values and their collections are immutable. Artifact names
and tags must be unique within their respective collections.

`CapabilityDescriptor` adds only the opaque discovery `entrypoint`. Discovery
does not import that entrypoint. Executable `Capability` values deliberately do
not contain an entrypoint.

## Manifest schema

Each catalog entry is a self-contained package with `manifest.yaml`:

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
  - name: file
    description: File path and UTF-8 text content.
tags:
  - repository
  - file
  - read
entrypoint: app.capabilities.read_file.implementation
```

All fields are required. `inputs` may be empty; `outputs` must contain at least
one artifact. Each artifact entry contains exactly `name` and `description`.
Unknown fields, unknown categories, duplicate artifact names, duplicate tags,
and empty values are rejected with the affected manifest path.

## Initial Capability Catalog

| Category | Capability | Inputs | Outputs | Implementation |
| --- | --- | --- | --- | --- |
| Repository | `ReadPullRequest` | `repository`, `pull_request_number` | `pull_request` | Available |
| Repository | `ReadChangedFiles` | `repository`, `pull_request_number` | `changed_files` | Available |
| Repository | `ReadFile` | `path` | `SourceCode` | Available |
| Analysis | `AnalyzeSourceCode` | `SourceCode` | `engineering_findings` | Ollama |
| Analysis | `MergeEngineeringFindings` | `engineering_findings[]` | `engineering_findings` | Available |
| Transformation | `GenerateMarkdown` | `engineering_findings` | `markdown` | Available |
| Publishing | `PublishGitHubComment` | `markdown` | `publication_result` | GitHub |

All six entries are discoverable today. A discoverable Capability does not imply
that its implementation exists or has been loaded. This keeps catalog design
independent from implementation lifecycle.

## Repository Capability behavior

`ReadPullRequest` reads provider-neutral pull-request data. Its output artifact
contains a JSON-compatible mapping supplied by the configured repository reader.

`ReadChangedFiles` reads provider-neutral changed-file records. Its output is a
JSON-compatible list suitable for later analysis or transformation
Capabilities.

`ReadFile` reads a path as UTF-8 text and produces a `SourceCode` artifact:

```json
{
  "path": "path/to/file.py",
  "content": "..."
}
```

The pull-request implementations depend on the small `RepositoryReader`
protocol inside the Capability ecosystem. A concrete GitHub adapter can satisfy
that protocol in a future epic, but neither GitHub nor provider selection is
part of this catalog. `ReadFileImplementation` uses local filesystem access by
default and accepts a replacement file-reading function for isolated testing.

These dependencies belong to implementations. They are never visible to
`ExecutionEngine`, `CapabilityRequest`, `CapabilityResult`, `ExecutionContext`,
workflow definitions, or execution plans.

`AnalyzeSourceCode` consumes the `SourceCode` artifact directly and produces
structured `EngineeringFindings`. See
[Engineering Intelligence](engineering-intelligence.md) for its knowledge model
and provider-isolation boundary.

`MergeEngineeringFindings` combines ordered per-source analyses into the single
knowledge object expected by downstream transformations. See
[Engineering Knowledge Aggregation](engineering-knowledge-aggregation.md).

`GenerateMarkdown` renders those findings as a deterministic
`MarkdownDocument`. See
[Engineering Communication](engineering-communication.md) for the rendering and
safety contract.

`PublishGitHubComment` delivers that document unchanged behind the
provider-neutral publishing boundary. See
[Engineering Delivery](engineering-delivery.md) for result and failure
contracts.

## Architectural boundary

```text
Manifest
   |
   v
CapabilityDescriptor  (discovery metadata only)

Capability             (WHAT, including public metadata)
   |
   v
CapabilityImplementation  (HOW)
   |
   `-- optional infrastructure dependency (WITH WHAT)
```

Metadata does not perform execution, select an implementation, resolve a
provider, or validate workflow dependencies. The Runtime remains stable while
catalog packages evolve independently.

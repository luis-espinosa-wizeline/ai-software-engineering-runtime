# First End-to-End Engineering Workflow

`pull-request-engineering-review` is the first production workflow assembled
entirely from the Runtime's existing declarative and execution contracts.

```text
Pull Request inputs
        |
        v
ReadChangedFiles
        |
        v  iteration
ReadFile
        |
        v  iteration
AnalyzeSourceCode
        |
        v
MergeEngineeringFindings
        |
        v
GenerateMarkdown
        |
        v
PublishGitHubComment
```

## Discovery and execution

`ProjectLoader` reads `runtime.yaml` and discovers
`workflows/pull-request-engineering-review.yaml`. The discovered
`WorkflowDefinition` can be resolved by its exact workflow id and version,
compiled by `ExecutionPlanner`, and executed by `ExecutionEngine`.

The workflow declares `repository` as a required string and
`pull_request_number` as a required integer. The Host validates those structural
inputs before execution. Provider configuration remains implementation-owned: the
repository reader, Ollama client, and GitHub publisher are supplied to their
respective Capability implementations, never to the workflow or Runtime.

## Artifact flow

`ReadChangedFiles` emits the ordered file collection. Runtime iteration expands
that collection for `ReadFile`, collects the resulting `SourceCode` Artifacts,
then expands those for `AnalyzeSourceCode`. Capabilities remain unaware of
iteration.

The resulting ordered collection of `EngineeringFindings` is merged by
`MergeEngineeringFindings`, because combining Engineering Knowledge is business
semantics. `GenerateMarkdown` creates one final document, and
`PublishGitHubComment` delivers that exact document once.

Source-file, line-range, and rule provenance remain in the structured findings
through analysis and aggregation and are represented in the generated
document.

## Architectural result

The workflow required no changes to the Runtime, planner, engine, execution
patterns, Artifact contracts, or existing Capability responsibilities. It
validates the intended extension model:

- new product behavior is composed declaratively;
- Artifacts are the only communication between Capabilities;
- the Runtime owns deterministic orchestration;
- Capabilities own Engineering semantics; and
- Providers remain isolated behind Capability implementations.

Future workflows can reuse the same Capabilities and execution patterns without
special-case orchestration.

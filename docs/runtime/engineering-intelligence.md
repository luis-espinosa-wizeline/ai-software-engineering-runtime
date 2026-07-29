# Engineering Intelligence

Engineering Intelligence is the Capability ecosystem layer that transforms
engineering inputs into reusable knowledge. It does not change Runtime
orchestration and is not tied to a presentation or publishing destination.

```text
ReadFile
    |
    v
SourceCode Artifact
    |
    v
AnalyzeSourceCode
    |
    v
engineering_findings Artifact
```

## AnalyzeSourceCode

`AnalyzeSourceCode` is an Analysis Capability:

- input: `SourceCode`;
- output artifact: `engineering_findings`, containing `EngineeringFindings`;
- contract: `AnalyzeSourceCode`;
- version: `"1"`.

`SourceCode` contains a JSON-compatible mapping with `path` and UTF-8 `content`.
Both values are required. The path is the authoritative source identity used
for every finding produced from that artifact.

`EngineeringFindings` contains a `findings` collection. Every
`EngineeringFinding` has:

- `summary`: concise observation;
- `source_file`: non-empty path identifying the analyzed source;
- `start_line` and `end_line`: optional one-based inclusive location;
- `rule_id`: optional provider-neutral rule identifier;
- `severity`: `info`, `low`, `medium`, `high`, or `critical`;
- `confidence`: number from 0 through 1;
- `category`: provider-neutral engineering concern;
- `explanation`: why the issue matters; and
- `recommendation`: actionable remediation.

An empty collection is valid and means the analyzer produced no findings.
`end_line` requires `start_line` and cannot precede it. Unknown fields, blank
context values, invalid line ranges, and invalid severity or confidence values
are rejected.

The artifact is engineering knowledge—not Markdown, a GitHub comment, or other
presentation. Future transformation and publishing Capabilities can consume the
same findings independently.

## Ollama implementation

`AnalyzeSourceCodeOllamaImplementation` is the first implementation. It is
configured with an Ollama model name and optionally an `httpx.Client`. Without
an injected client, it calls the local Ollama default at
`http://localhost:11434/api/chat`.

The implementation:

1. validates the `SourceCode` artifact;
2. sends the source to Ollama's non-streaming chat API;
3. supplies the `EngineeringFindings` JSON Schema as the structured-output
   `format`;
4. uses temperature zero for more deterministic structured output;
5. validates the returned message content with the domain model;
6. replaces model-supplied `source_file` values with the authoritative
   `SourceCode.path`; and
7. emits one `engineering_findings` artifact containing that domain value.

This follows Ollama's official
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
and [chat API](https://docs.ollama.com/api/chat) contracts.

Transport failures and malformed model output raise `OllamaAnalysisError`.
Those errors contain no provider behavior in the Runtime; they remain local to
the implementation package.

## Provider isolation

Only `app.capabilities.analyze_source_code` imports or names Ollama. The
`Capability`, manifests, artifacts, `CapabilityRequest`, `CapabilityResult`,
resolver, Execution Engine, context, plans, and workflows remain
provider-neutral.

No provider selection is implemented. The resolver continues to receive one
implementation for each Action Contract. A future implementation can use a
different reasoning technology while preserving the same Capability and
artifact contracts.

No workflow, Markdown generation, or GitHub behavior is introduced by this
layer.

A single analysis can be passed unchanged to `GenerateMarkdown`. When iteration
produces multiple analyses, `MergeEngineeringFindings` first creates one
knowledge object. See
[Engineering Knowledge Aggregation](engineering-knowledge-aggregation.md) and
[Engineering Communication](engineering-communication.md).

The provenance contract is described in
[Engineering Finding Context](engineering-finding-context.md).

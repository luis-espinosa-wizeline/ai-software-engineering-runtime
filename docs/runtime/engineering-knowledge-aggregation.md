# Engineering Knowledge Aggregation

Runtime iteration deliberately produces one analysis payload for every input:

```text
SourceCode[]
        |
        v  Runtime iteration
AnalyzeSourceCode
        |
        v
engineering_findings[]  # ordered collection
```

Combining those analyses is business semantics rather than execution semantics.
The Runtime cannot decide how domain objects should merge without learning their
meaning. `MergeEngineeringFindings` therefore performs that refinement as an
ordinary provider-neutral Capability.

## Contract

`MergeEngineeringFindings` is an Analysis Capability:

- input artifact: `engineering_findings`, with a list of validated
  `EngineeringFindings` payloads;
- output artifact: `engineering_findings`, with one validated
  `EngineeringFindings` payload; and
- implementation: `MergeEngineeringFindingsImplementation`.

Using the same artifact name preserves the domain meaning while the payload
cardinality changes from a collection to one aggregate value.

## Deterministic behavior

The implementation concatenates findings in:

1. outer collection order; then
2. each `EngineeringFindings.findings` order.

It does not sort, deduplicate, analyze, summarize, modify severity or confidence,
generate recommendations, or infer file context. Each immutable finding,
including its `source_file`, optional line range, and optional `rule_id`, is
carried into the aggregate unchanged. Empty collections and collections
containing empty analyses produce an empty `EngineeringFindings`. Malformed
collection members are rejected.

## Composition

```text
ReadChangedFiles
        |
        v
changed_files[]
        |
        v  iteration
ReadFile
        |
        v
SourceCode[]
        |
        v  iteration
AnalyzeSourceCode
        |
        v
engineering_findings[]
        |
        v
MergeEngineeringFindings
        |
        v
engineering_findings
        |
        v
GenerateMarkdown
```

`GenerateMarkdown` continues to consume one `EngineeringFindings` value without
knowing that upstream analysis used iteration. The Runtime retains ownership of
collection expansion; the aggregation Capability retains ownership of
Engineering Knowledge semantics.

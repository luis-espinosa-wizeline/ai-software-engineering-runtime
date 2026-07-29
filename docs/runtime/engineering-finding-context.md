# Engineering Finding Context

An `EngineeringFinding` describes both what was detected and where it
originated. Source provenance is Engineering Knowledge: downstream
Capabilities need it to explain, aggregate, render, or otherwise reuse a
finding without reconstructing context from workflow state.

## Domain contract

Every finding contains:

- `source_file`: required, non-empty source identity;
- `start_line`: optional one-based starting line;
- `end_line`: optional one-based ending line, valid only with `start_line` and
  never before it; and
- `rule_id`: optional, non-empty provider-neutral analysis rule identifier.

The location fields describe knowledge produced by analysis. They contain no
Ollama, GitHub, HTTP, presentation, or publishing metadata.

## Context ownership

`AnalyzeSourceCode` owns context creation. Its Ollama implementation requests
structured location data, validates it, and always assigns `source_file` from
the input `SourceCode.path`. A model therefore cannot replace the authoritative
source identity. Line ranges and rule identifiers remain optional because an
analysis may identify a valid concern without either value.

`MergeEngineeringFindings` retains each finding and its context without
modification. `GenerateMarkdown` presents the source and any available line and
rule context, but the structured `EngineeringFinding` remains the canonical
source of truth.

```text
SourceCode(path, content)
        |
        v
AnalyzeSourceCode
        |
        v
EngineeringFinding(source_file, lines, rule_id, meaning)
        |
        v
MergeEngineeringFindings
        |
        v
GenerateMarkdown
```

This evolution requires no changes to planning, execution, iteration, context,
resolution, or workflow models. The Runtime continues to transport Artifacts
without knowing the additional domain fields.

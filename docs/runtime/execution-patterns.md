# Execution Patterns

Execution patterns describe how the Runtime invokes otherwise ordinary
Capabilities. Capabilities continue to implement one business transformation
and communicate only through Artifacts.

The Runtime currently supports sequence and deterministic iteration.
Parallelism, conditions, retries, scatter/gather, nested iteration, and dynamic
planning are not implemented.

## Deterministic iteration

An iterated step identifies one of its existing input binding parameters:

```yaml
- id: read_files
  action: ReadFile
  inputs:
    path:
      step_output:
        step: changed_files
        artifact: changed_files
  outputs:
    - SourceCode
  iteration:
    input: path
```

The referenced binding must resolve to an Artifact whose payload is a list. For
each list element, in list order, the Execution Engine:

1. creates an input Artifact named for the iterated parameter and containing
   that element;
2. keeps every non-iterated binding unchanged;
3. constructs the ordinary `CapabilityRequest`;
4. invokes the ordinary `CapabilityImplementation`; and
5. collects each declared output payload.

After all invocations succeed, the engine stores one Artifact for every declared
step output. Each aggregate Artifact retains the declared output name and has a
list payload in invocation order:

```text
Artifact<List<T>>
        |
        v
iteration over Capability(T -> R)
        |
        v
Artifact<List<R>>
```

An empty input collection performs no invocations and produces an empty list for
every declared output. Every invocation must produce exactly the output names
declared by the iterated step. A non-list input raises
`IterationInputNotCollection`; missing, duplicate, or unexpected outputs raise
`IterationOutputMismatch`. Capability failures propagate normally. Aggregate
artifacts are stored only after every invocation succeeds.

## Determinism and isolation

Iteration is sequential. Input order determines invocation order and aggregate
output order. It does not sort, prioritize, parallelize, retry, or reinterpret
payloads.

Capabilities receive the same request shape whether invoked once or through
iteration. They receive no plan, iteration index, collection, engine, or context
object. Providers remain confined to their implementations.

This keeps collection expansion in the Runtime and prevents batch variants such
as `ReadFiles` or `AnalyzeFiles` from duplicating focused Capability behavior.

## Current engineering composition

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
```

The final iteration value is deliberately a collection of individual
`EngineeringFindings` payloads. Combining those domain values is not iteration
behavior; the provider-neutral `MergeEngineeringFindings` Capability owns that
business transformation. See
[Engineering Knowledge Aggregation](engineering-knowledge-aggregation.md).

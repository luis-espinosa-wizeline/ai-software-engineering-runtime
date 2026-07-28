# Execution Context

## Responsibility

`ExecutionContext` is the mutable working memory of one `ExecutionPlan`
execution. It belongs to exactly one execution, identifies the plan being run,
stores the inputs supplied for that run, and accumulates artifacts produced by
completed workflow steps.

```text
WorkflowDefinition    declarative intent
        |
        v
ExecutionPlanner      deterministic planning
        |
        v
ExecutionPlan         immutable execution strategy
        |
        v
ExecutionContext      mutable state for one execution
```

The separation is intentional: definitions describe intent, the planner compiles
that intent, plans describe strategy, and contexts hold evolving runtime state.
An execution context knows the identity of its execution and execution plan. It
does not know the originating `WorkflowDefinition`.

## Execution Inputs

Inputs are the concrete values supplied for one execution. The execution plan
declares which inputs are required; the execution context stores their values.
This keeps reusable plans independent from repository names, request values, and
other run-specific data.

The context does not resolve input bindings or navigate plan steps. Those are
responsibilities of the `ExecutionEngine`.

## Artifacts

An `Artifact` is a named piece of work produced by a capability and consumed by
later workflow steps. Its minimal model contains:

- a name;
- a provider-neutral payload; and
- optional metadata describing characteristics useful to downstream consumers.

The Runtime preserves and transports artifacts but never interprets their
payloads. Artifacts do not introduce storage identifiers, timestamps, versions,
persistence rules, serialization strategies, or transport abstractions.

Artifacts are stored by producing step and artifact name:

```text
step_id
    artifact_name -> Artifact
```

This structure mirrors `ExecutionPlan` step-output references and makes lookup
deterministic. An artifact cannot overwrite another artifact with the same name
for the same step. The same artifact name may be used by different steps because
the producing step is part of its lookup location.

## Mutation Ownership

Only the `ExecutionEngine` may mutate an execution context. Capabilities are pure
artifact producers: they receive values and artifacts and return artifacts. They
never receive or mutate the context itself. The engine communicates with them
only through `CapabilityRequest` and `CapabilityResult`.

```text
Artifacts -> Capability -> Artifacts
                            |
                            v
                 ExecutionEngine stores them
                            |
                            v
                  ExecutionContext
```

The context encapsulates artifact storage through `store_artifact`,
`get_artifact`, and `has_artifact`. Runtime components do not receive its internal
step-artifact mapping.

## Deliberate Exclusions

`ExecutionContext` does not execute or orchestrate work. It contains no workflow
definition, provider, LLM, capability implementation, execution-engine
implementation, lifecycle status, retry behavior, logging, telemetry,
persistence, audit history, event stream, trace, or distributed-execution
behavior.

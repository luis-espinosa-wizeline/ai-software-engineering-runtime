# Execution Engine

## Responsibility

The `ExecutionEngine` deterministically executes an immutable `ExecutionPlan`.
It introduces no workflow or business decisions: the planner has already
selected the steps, their order, their dependencies, and the declared workflow
result.

```text
ExecutionPlan
      |
      v
ExecutionEngine
      |
      v
Step Execution Lifecycle
      |
      v
CapabilityRequest
      |
      v
CapabilityImplementation
      |
      v
CapabilityResult
      |
      v
ExecutionContext
      |
      v
Workflow Result Artifact
```

Plan steps execute in declared order. A normal step is invoked once; a step with
the iteration pattern is invoked once per collection element, sequentially. See
[Execution Patterns](execution-patterns.md).

## Uniform Step Lifecycle

For each plan step, the engine:

1. resolves every input binding from execution inputs or previously stored
   artifacts;
2. wraps every resolved binding as a named input artifact;
3. constructs a `CapabilityRequest` containing the step's Capability and those
   artifacts;
4. resolves and invokes the implementation for that Action Contract;
5. receives a `CapabilityResult`; and
6. stores every returned artifact under the producing step in the
   `ExecutionContext`.

No step knows its position in the workflow. Implementations receive only a
`CapabilityRequest` and return only a `CapabilityResult`; they never receive the
plan or context. Artifacts are the only values crossing the execution boundary.
The engine owns all context mutation.

## Input Binding Resolution

A `PlanInputReference` resolves to the corresponding concrete value in
`ExecutionContext.inputs`. A `StepOutputReference` resolves to the named artifact
stored for the referenced step. The engine creates a new input artifact named
for the target action parameter and copies the resolved payload and metadata.
Consequently, implementations receive artifacts without learning how or where
the execution context stores them.

Missing execution inputs and missing referenced artifacts fail deterministically
before the affected capability is invoked.

## Capability Resolution

The engine locates implementations through the provider-neutral
`CapabilityResolver` contract. `InMemoryCapabilityResolver` is the minimal
deterministic implementation: it snapshots implementations by Action Contract
and does not contain provider logic, infrastructure configuration, provider
selection, or a dependency injection framework.

Resolution fails explicitly when an Action Contract has no capability or when
multiple capabilities declare the same Action Contract.

## Declarative Workflow Completion

After every step has completed, the engine resolves `ExecutionPlan.result`
against the execution context and returns that artifact. It never returns the
last artifact merely because it was produced last. The result therefore remains
the declarative choice preserved by the planner from the workflow definition.

Execution fails if the declared result artifact was not produced. The engine
does not infer an alternative result.

## Deterministic Scope

Given the same plan, inputs, resolver snapshot, and deterministic capabilities,
the engine invokes capabilities in the same order, constructs the same requests,
stores artifacts under the same step identifiers, and resolves the same declared
result.

The engine does not implement parallelism, retries, recovery, compensation,
scheduling, timeouts, persistence, execution history, telemetry, cancellation,
distributed execution, or provider-specific integrations. Iteration remains
ordered and synchronous.

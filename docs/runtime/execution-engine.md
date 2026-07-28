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
 Capability
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

Execution is sequential. The engine traverses the plan's steps in declared order
and applies the same lifecycle to every step. It does not distinguish first,
intermediate, last, or single-workflow steps.

## Uniform Step Lifecycle

For each plan step, the engine:

1. resolves every input binding from execution inputs or previously stored
   artifacts;
2. constructs a `CapabilityRequest` containing the step's Action Contract and
   fully resolved values;
3. resolves the capability implementing that Action Contract;
4. invokes the capability;
5. receives a `CapabilityResult`; and
6. stores every returned artifact under the producing step in the
   `ExecutionContext`.

No step knows its position in the workflow. Capabilities receive only a
`CapabilityRequest` and return only a `CapabilityResult`; they never receive the
plan or context. The engine owns all context mutation.

## Input Binding Resolution

A `PlanInputReference` resolves to the corresponding concrete value in
`ExecutionContext.inputs`. A `StepOutputReference` resolves to the payload of the
named artifact stored for the referenced step. Consequently, capability requests
contain values rather than Runtime references or artifacts tied to context
storage.

Missing execution inputs and missing referenced artifacts fail deterministically
before the affected capability is invoked.

## Capability Resolution

The engine locates capabilities through the provider-neutral
`CapabilityResolver` contract. `InMemoryCapabilityResolver` is the minimal
deterministic implementation: it snapshots capabilities by Action Contract and
does not contain provider logic, infrastructure configuration, or a dependency
injection framework.

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
distributed execution, or provider-specific integrations.

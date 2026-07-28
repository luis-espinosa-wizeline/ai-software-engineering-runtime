# Execution Contracts

## Responsibility

Execution contracts are the provider-neutral communication boundary between the
`ExecutionEngine` and executable capabilities. They define the messages and
interface used for collaboration without introducing provider behavior.

```text
ExecutionEngine
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
ExecutionEngine stores artifacts
       |
       v
ExecutionContext
```

The engine prepares a request from resolved plan inputs and artifacts. A
capability performs the requested work and returns artifacts. The engine, not the
capability, stores those artifacts in the execution context.

## Capability

A `Capability` is an executable implementation of one declared Action Contract.
Its interface identifies that Action Contract and transforms a
`CapabilityRequest` into a `CapabilityResult`.

Capabilities are pure units of work at the Runtime boundary. They receive fully
prepared input values and return artifacts. They do not resolve workflow
references, navigate a plan, or mutate runtime state.

A capability never receives or knows a `WorkflowDefinition`, `ExecutionPlan`,
`ExecutionContext`, `ExecutionEngine`, or other Runtime internals. Conversely,
the Runtime contract contains no provider, OpenAI, Ollama, HTTP, SDK, or
infrastructure concept.

## Capability Request

A `CapabilityRequest` contains:

- the provider-neutral Action Contract to perform; and
- fully resolved input values.

It contains no plan bindings, workflow references, execution context, execution
plan, or other Runtime objects. Preparing this message is an `ExecutionEngine`
responsibility.

## Capability Result

A `CapabilityResult` contains one or more artifacts produced by the capability.
Artifacts are transported unchanged across the execution boundary. The result
does not contain status, retries, metrics, duration, token usage, provider
metadata, timestamps, or errors.

Capability lookup uses the provider-neutral `CapabilityResolver` contract.
Provider selection, scheduling, retries, telemetry, and persistence remain
outside these contracts.

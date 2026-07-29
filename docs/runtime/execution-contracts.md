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
CapabilityImplementation
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

A `Capability` is an immutable, provider-neutral description of WHAT
transformation may be requested. Its `contract` identifies that transformation.
It has no execution method, provider, configuration, or implementation logic.

## Capability Implementation

A `CapabilityImplementation` defines HOW one Capability is performed. The
structural protocol exposes its Capability and transforms a `CapabilityRequest`
into a `CapabilityResult`. Implementations receive named input artifacts and
produce output artifacts.

An implementation never receives or knows a `WorkflowDefinition`,
`ExecutionPlan`, `ExecutionContext`, `ExecutionEngine`, or other Runtime
internals. The engine owns context access and mutation. This preserves minimum
knowledge while still providing the implementation all resolved data needed for
one invocation.

An implementation may privately use a provider such as a filesystem, model API,
container runtime, or remote service. Providers are WITH WHAT the transformation
is performed. They are intentionally absent from every Runtime contract, so
provider technology can change without affecting planning or execution.

## Capability Request

A `CapabilityRequest` contains:

- the provider-neutral `Capability` to perform; and
- fully resolved, uniquely named input artifacts.

It contains no plan bindings, workflow references, execution context, execution
plan, or other Runtime objects. Preparing this message is an `ExecutionEngine`
responsibility.

## Capability Result

A `CapabilityResult` contains one or more artifacts produced by the capability.
Artifacts are transported unchanged across the execution boundary. The result
does not contain status, retries, metrics, duration, token usage, provider
metadata, timestamps, or errors.

Capability implementation lookup uses the provider-neutral `CapabilityResolver`
contract. The current resolver allows exactly one implementation per contract.
The protocol permits different implementation classes, but selection among
multiple implementations, provider selection, scheduling, retries, telemetry,
and persistence remain outside these contracts.

`IdentityCapabilityImplementation` is the minimal working example. It reads a
`value` artifact and produces a `result` artifact without any provider.

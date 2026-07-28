# Runtime Architecture

## Overview

The Runtime coordinates software engineering work from initiation through
publication. Its architecture separates durable domain concepts from the
technologies that deliver events, fulfill capabilities, execute tools, persist
state, or receive results.

```text
WorkflowDefinition
        |
        v
 Execution Planner
        |
        v
  ExecutionPlan
        |
        v
ExecutionContext
        |
        v
 Policy Evaluation
        |
        v
 Execution Engine
        |
        v
 Execution Result
```

A workflow definition expresses intent. Before any work is performed, the
Execution Planner translates that intent into an execution plan. The plan
expresses the provider-neutral strategy for satisfying the workflow. Policy
evaluates that strategy before the Execution Engine coordinates it and produces a
result.

The Runtime executes plans, not workflow definitions directly. An
`ExecutionContext` provides the mutable state for one plan execution. These
boundaries keep declarative workflow intent, deterministic planning, mutable
runtime state, and execution as separate architectural concerns.

## Major Building Blocks

### Runtime

The Runtime is the coordinating boundary. It accepts work, selects a workflow,
establishes an execution, and governs its progress to a terminal outcome.

### Triggers and Requests

Triggers represent configured sources of work, while trigger events and explicit
requests capture why an execution begins. They translate external intent into
provider-neutral Runtime input.

### Workflow Definitions

A workflow definition is a declarative model of a versioned engineering process.
It expresses reusable workflow intent through inputs, steps, action contracts,
bindings, outputs, a result, and any required capabilities or prerequisites. It
does not express execution behavior.

Definitions intentionally exclude providers, runtime configuration, retries,
execution status, execution context, execution data, and policy decisions. Those
concerns belong to later Runtime components.

### Discovery and Registry

Discovery locates workflow definitions. The registry validates and organizes
them into a deterministic catalog, including active-version and availability
queries. Together they make workflows available to the Runtime without coupling
execution to a discovery mechanism.

### Execution Planning

Execution planning deterministically translates a selected workflow definition
into an immutable execution plan before execution begins. Like a compiler, the
planner validates workflow semantics and resolves declarative references. Given
the same definition, it always produces the same plan.

The planner preserves declared action contracts. It does not optimize or infer
behavior, select providers, resolve required capabilities, or execute them.
Planning is the boundary between describing desired work and producing the
provider-neutral strategy that later Runtime components consume.

The current model also requires every workflow step to contribute to the declared
workflow result through the dependency graph. Planning rejects disconnected or
dead steps. This intentionally excludes effect-only work; a future model may
explicitly support steps for auditing, telemetry, notifications, or logging.

### Workflow Execution

A workflow execution is the central record of one workflow run. It owns lifecycle
state, step progress, capability activity, policy decisions, and the final
workflow result. This gives the Runtime one coherent boundary for observing and
auditing an outcome.

### Context

An `ExecutionContext` is the mutable working memory of exactly one execution
plan run. It knows the execution and plan identifiers, stores concrete execution
inputs, and stores artifacts by producing step and artifact name. It does not
know the originating workflow definition, providers, capability implementations,
or the execution-engine implementation.

Artifacts are named, provider-neutral units of information produced by
capabilities and consumed by later steps. The Runtime preserves and transports
their payloads without interpreting them. Only the Execution Engine may store
artifacts in the context; capabilities produce artifacts but never mutate the
context.

### Capabilities and Providers

A capability is an executable implementation of a declared Action Contract. It
accepts a provider-neutral `CapabilityRequest` containing fully resolved inputs
and returns a `CapabilityResult` containing artifacts. This execution contract
isolates Runtime orchestration from any provider, model, service, SDK, transport,
or infrastructure used by an implementation.

Capabilities do not receive workflow definitions, execution plans, execution
contexts, the execution engine, or other Runtime internals. They do not resolve
workflow references or mutate context. The future Execution Engine prepares
requests and owns storing returned artifacts in the ExecutionContext.

Required capabilities and action contracts have different roles. An action
contract identifies the provider-neutral operation a step intends to perform—what
should happen. A required capability identifies a capability or prerequisite
needed by a workflow or step, but not the executable operation itself. Resolving
required capabilities is outside the Execution Planner.

### Policy Evaluation

Policy validates or modifies an execution strategy before execution and may
constrain behavior throughout its lifecycle. It provides a consistent governance
boundary regardless of the workflow or technology involved.

### Execution Engine

The Execution Engine executes an approved plan sequentially in its declared
order. For every step it resolves bindings from the ExecutionContext, constructs
a fully resolved CapabilityRequest, resolves and invokes the capability, and
stores every returned artifact. This lifecycle is identical for first,
intermediate, last, and single-workflow steps.

After all steps complete, the engine retrieves the artifact named by the plan's
result reference. It never infers completion from the last step or last artifact.
The engine therefore coordinates execution without making workflow decisions.
Capabilities receive no plan or context; context mutation remains owned by the
engine.

### Results and Publishers

Workflow results express provider-neutral outcomes. Publishers deliver those
outcomes to external destinations without making the domain depend on a
particular repository host or communication channel.

## Conceptual Relationships

Definitions are discovered and registered before they are selected for execution.
A selected definition is planned, the resulting strategy is evaluated by policy,
and only then is it coordinated by the Execution Engine. Each workflow execution
belongs to one definition and carries the complete state of one run. Context
informs execution, capabilities supply the required technical behavior, and
providers fulfill concrete integrations. Execution produces a result, which a
publisher can translate for an external destination.

External technologies participate through adapters around these boundaries. They
may change independently; the Runtime concepts and their responsibilities remain
stable.

## Contracts

Execution contracts define the provider-neutral communication boundary between
the future Execution Engine and capabilities:

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
ExecutionContext
```

The request identifies the Action Contract and carries fully resolved values. A
capability performs the work and returns one or more artifacts. The engine owns
all ExecutionContext mutation.

Future Runtime evolution may introduce:

- Workflow Contracts
- Human Approval Contracts

These additional contract types remain evolution points rather than current
domain models.

## Runtime Responsibilities

- **WorkflowDefinition:** describes declarative intent.
- **Execution Planner:** deterministically validates and compiles intent.
- **ExecutionPlan:** describes the immutable, provider-neutral execution
  strategy.
- **ExecutionContext:** holds the mutable inputs and artifacts for one plan
  execution.
- **Policy Engine:** validates or modifies the execution strategy.
- **Execution Engine:** coordinates execution.
- **Capabilities:** implement technical behavior.
- **Providers:** execute concrete integrations.

These responsibilities compose into Runtime behavior while remaining independently
understandable.

## Design Philosophy

Simple does not mean limited. Simple means composing small responsibilities into
complex behavior.

The Runtime should preserve clear boundaries between intent, planning, policy,
coordination, technical behavior, and integration. New abstractions should emerge
from demonstrated Runtime needs rather than anticipated complexity.

## Future Evolution

The Runtime may eventually support workflow composition through additional
contract types. This direction would allow workflows to express dependencies on
other workflow outcomes or human decisions while preserving the separation
between intent and execution strategy. The shape of that evolution remains
intentionally deferred until a concrete capability requires it.

# Runtime Architecture

## Overview

The Runtime coordinates software engineering work from initiation through
publication. Its architecture separates durable domain concepts from the
technologies that deliver events, fulfill capabilities, execute tools, persist
state, or receive results.

```text
Project directory
        |
        v
 ProjectLoader
        |
        v
    Project
        |-- WorkflowDefinitions
        `-- CapabilityDescriptors
        |
        v
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

Project discovery precedes this stable planning and execution chain.
`ProjectLoader` creates an immutable snapshot of declarative resources; it does
not select, plan, resolve, import, instantiate, or execute them. See
[Project Discovery](runtime/project-discovery.md) for the supported filesystem
layout and YAML schemas.

The Runtime executes plans, not workflow definitions directly. An
`ExecutionContext` provides the mutable state for one plan execution. These
boundaries keep declarative workflow intent, deterministic planning, mutable
runtime state, and execution as separate architectural concerns.

External event handling and dependency assembly sit outside that chain. The
provider-neutral Runtime Host SPI selects an existing workflow, obtains a
configured resolver, creates the plan and context, and invokes the Execution
Engine exactly once. Before composition, it validates normalized event inputs
against the selected Workflow's retained structural input definitions. It never
performs step execution or Artifact transformation. See
[Runtime Host SPI](runtime/runtime-host-spi.md) and
[Workflow Input Contracts](runtime/workflow-input-contracts.md).

The first concrete adapter is the
[GitHub Runtime Host](runtime/github-runtime-host.md). It verifies and
normalizes pull-request webhooks, resolves a GitHub App installation token,
prepares an execution-scoped exact-SHA workspace, and supplies a
workspace-aware `CapabilityComposition`. These dependencies point inward
through the Host SPI; the Execution Core has no GitHub or workspace dependency.

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

Project discovery additionally locates self-contained capability manifests.
These produce metadata-only `CapabilityDescriptor` values and remain independent
of executable capability resolution. A discovered `Project` contains workflow
definitions and descriptors directly; no project-level registry is required.

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

A Capability defines WHAT provider-neutral transformation the Runtime may
request. It is an immutable domain value identified by its Action Contract and
contains no execution behavior. Its public metadata also declares its name,
description, category, version, input and output Artifacts, and discovery tags.
The same metadata is available on descriptors during project discovery, making
Capabilities understandable before implementations are loaded.

A Capability Implementation defines HOW that transformation is performed. Every
implementation satisfies the same structural `CapabilityImplementation`
protocol: it identifies its Capability, receives a `CapabilityRequest` containing
named input Artifacts, and returns a `CapabilityResult` containing output
Artifacts. The Execution Engine depends only on this protocol and never on a
concrete implementation.

A Provider is an optional infrastructure dependency used by an implementation:
for example a filesystem, model API, repository service, or container runtime.
It describes WITH WHAT technology an implementation works. Providers are
completely invisible to the Runtime and do not occur in workflow, plan, engine,
resolver, request, result, artifact, or context contracts.

```text
WHAT                 HOW                         WITH WHAT
Capability
    |
    v
Capability Implementation  ---- optionally ----> Provider
```

Implementations do not receive workflow definitions, execution plans, execution
contexts, the execution engine, or other Runtime internals. They do not resolve
workflow references or mutate context. The Execution Engine prepares input
Artifacts and owns storing returned Artifacts in the ExecutionContext. This
keeps Artifacts as the universal execution language and gives each component
only the knowledge it needs.

Different implementation classes may realize the same Capability. The current
Runtime intentionally requires one implementation per Action Contract; choosing
among multiple implementations and selecting providers are future concerns.
The initial public catalog and manifest contract are documented in
[Capability Metadata and Catalog](runtime/capability-catalog.md).

### Engineering Intelligence

Engineering Intelligence is built from ordinary Capabilities rather than added
to the Runtime. `AnalyzeSourceCode` transforms a `SourceCode` Artifact into an
`engineering_findings` Artifact containing structured `EngineeringFindings`
source provenance, severity, confidence, category, explanation, and
recommendation data. Source context is part of the Engineering Knowledge domain
and passes through Runtime Artifacts without Runtime interpretation. See
[Engineering Finding Context](runtime/engineering-finding-context.md).

Its Ollama implementation is confined to the Capability package. The Runtime
sees the same provider-neutral Capability request and result contracts it uses
for repository operations. Presentation and publishing remain separate
downstream transformations. See
[Engineering Intelligence](runtime/engineering-intelligence.md).

Per-source analyses produced through iteration remain an ordered collection.
`MergeEngineeringFindings` combines them as an ordinary Analysis Capability,
because merging Engineering Knowledge is business semantics rather than Runtime
execution semantics. See
[Engineering Knowledge Aggregation](runtime/engineering-knowledge-aggregation.md).

### Engineering Communication

Engineering Communication transforms structured knowledge into human-readable
representations without changing that knowledge. `GenerateMarkdown`
deterministically renders `engineering_findings` into a `markdown` Artifact
whose payload is a `MarkdownDocument`.

The implementation uses no AI model or provider and contains no publishing
behavior. A later delivery Capability can consume the document without coupling
analysis or presentation to its destination. See
[Engineering Communication](runtime/engineering-communication.md).

### Engineering Delivery

Engineering Delivery sends final documents to external systems without changing
them. `PublishGitHubComment` consumes a `markdown` Artifact and emits a
provider-neutral `publication_result`.

The Capability Implementation depends on `EngineeringPublisher`; the concrete
GitHub adapter alone knows repository targeting, pull-request numbers,
authentication, HTTP paths, and provider responses. Delivery failures are mapped
to domain errors before crossing that boundary. See
[Engineering Delivery](runtime/engineering-delivery.md).

### First End-to-End Engineering Workflow

The declarative `pull-request-engineering-review` workflow composes repository
reading, Runtime iteration, source analysis, knowledge aggregation, Markdown
generation, and GitHub delivery. It uses the existing discovery, planning,
execution, Artifact, Capability, and provider boundaries without introducing
workflow-specific Runtime behavior. See
[First End-to-End Engineering Workflow](runtime/first-engineering-workflow.md).

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

An execution-plan step may declare deterministic iteration over one bound input.
The engine expands a list payload into ordered, ordinary Capability invocations
and aggregates each declared output into a list-valued Artifact. This changes
orchestration cardinality without changing Capability contracts or provider
isolation. See [Execution Patterns](runtime/execution-patterns.md).

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
CapabilityImplementation
       |
       v
CapabilityResult
       |
       v
ExecutionContext
```

The request identifies the Capability and carries fully resolved input Artifacts.
An implementation performs the work and returns one or more output Artifacts.
The engine owns all ExecutionContext mutation.

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
- **Capability:** defines WHAT transformation may be requested.
- **Capability Implementation:** defines HOW the transformation is executed.
- **Provider:** optional infrastructure known only by an implementation.

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

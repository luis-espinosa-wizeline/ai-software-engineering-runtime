# Execution Plan

## Responsibility

An `ExecutionPlan` is an immutable, provider-neutral description of how the
Runtime should execute a workflow. It is the execution strategy produced from
workflow intent and consumed by future execution behavior.

The Runtime executes plans rather than workflow definitions directly. A plan
orders required actions, connects their declared inputs and outputs, and identifies
the output that becomes the plan result. It does not execute code.

The workflow domain evolved to express the typed declarative inputs, action
contracts, bindings, outputs, and result reference needed to produce this
strategy. These core semantics are explicit fields rather than metadata because
they require stable typing and semantic validation. The workflow fields express
intent; they do not duplicate or replace the execution plan.

## Reusable Templates

Execution plans are reusable templates. A plan declares the inputs an execution
must supply but does not contain their concrete values. The same plan can
therefore guide many executions of the same workflow version without carrying
repository names, pull request numbers, credentials, timestamps, or other
execution-specific state between them.

## Runtime Concepts

- **WorkflowDefinition** expresses intent: the reusable engineering process and
  what it seeks to accomplish.
- **ExecutionPlan** expresses strategy: the ordered, provider-neutral actions and
  data relationships used to satisfy that intent.
- **ExecutionContext** is the mutable state of one plan execution. It contains
  concrete input values and artifacts produced by completed steps.
- **RuntimeConfiguration** represents installation or environment choices that
  influence Runtime behavior. It is outside the execution plan and is not
  introduced by this model.

Keeping these responsibilities separate prevents reusable strategy from becoming
coupled to one request, environment, or integration.

## Actions and Bindings

Each plan step names an action contract, binds action parameters to declared plan
inputs or outputs of earlier steps, and declares the outputs it produces. Action
contracts are opaque identifiers such as `code.analysis` or
`repository.retrieve_changes`. They represent the provider-neutral operation the
step intends to perform: what should happen, not how it is implemented.

Action contracts are distinct from required capabilities. A required capability
describes a capability or prerequisite needed by a workflow or step; it does not
identify the executable operation. Capability resolution occurs after planning.
The `ExecutionPlanner` only preserves the action contract declared by each
workflow step.

A step may additionally declare an `Iteration` naming one bound input parameter.
That execution metadata changes how many times the action is invoked without
changing its Action Contract, bindings, or Capability request/result contracts.
See [Execution Patterns](execution-patterns.md).

A plan input reference points to one of the plan's required inputs. A step output
reference points to an output declared by an earlier step. The final plan result
is likewise a reference to a declared step output.

## Provider Independence

Providers and AI models are intentionally excluded. A plan may require
`code.analysis`, but it does not select GPT-5, Claude, Gemini, a local model, or
any other implementation. Provider selection belongs to later Runtime behavior,
allowing a plan to remain stable as integrations and operational choices change.

## Execution-Specific Values

Concrete values belong to the `ExecutionContext` because they describe one run.
Putting them in an `ExecutionPlan` would turn a reusable strategy into
execution state, risk carrying values between runs, and couple planning to the
event or environment that supplied them.

Step outputs become named artifacts in the execution context. They are stored by
producing step and artifact name, mirroring `StepOutputReference`. The Runtime
preserves their provider-neutral payloads but does not interpret them.

## Pull Request Review Example

A Pull Request Review workflow definition expresses the intent to review a
change. Its execution plan could declare `repository` and `pull_request` as
required inputs, followed by two ordered steps:

1. `retrieve-changes` requires `repository.retrieve_changes`, binds its parameters
   to the required plan inputs, and declares a `changes` output.
2. `analyze-code` requires `code.analysis`, binds its input to the earlier
   `changes` output, and declares a `review` output.

The plan result references `analyze-code.review`. At execution time, the context
supplies the actual repository and pull request values. The plan names neither a
provider nor an execution engine.

# ADR-001: WorkflowExecution as the Runtime Aggregate Root

## Status

Accepted

## Context

Each run of a workflow creates related state: lifecycle status, step progress,
capability activity, policy decisions, and an eventual result. These records need
one consistent ownership boundary so that the progress and outcome of an execution
can be understood as a whole.

Workflow definitions describe reusable work, while executions record what happened
during one run. Mixing coordination across several independent objects would make
the execution lifecycle harder to observe and audit.

## Decision

`WorkflowExecution` is the Aggregate Root of the Runtime. Each
`WorkflowExecution` represents one execution of one `WorkflowDefinition`.

The aggregate owns:

- execution lifecycle state;
- workflow step executions;
- capability requests and results;
- policy decisions; and
- the eventual `WorkflowResult`.

All state describing the progress and outcome of a workflow execution belongs to
this aggregate. No other domain object coordinates execution state.

The aggregate remains technology-agnostic as established by
[ADR-003](003-technology-agnostic-domain-model.md).

## Consequences

- A complete execution can be observed and audited through one domain boundary.
- Step progress, capability activity, policy decisions, and results remain
  correlated with the execution that produced them.
- New execution-level records can be added without creating competing coordination
  boundaries.
- Changes to execution state must preserve the consistency of the aggregate.
- `WorkflowDefinition` remains a description of work and does not own runtime
  progress.

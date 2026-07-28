# ADR-002: Frozen Runtime Architecture

## Status

Accepted

## Context

The Runtime has reached its first stable architectural milestone. Its core domain
boundaries need to remain consistent while implementation work proceeds. Repeated
changes to those boundaries would make integrations, workflows, and supporting
infrastructure depend on a moving domain model.

Implementation details will continue to evolve as the Runtime is built. That
evolution must not implicitly redesign the established architecture.

## Decision

The Runtime architecture is intentionally frozen around these concepts:

- `Runtime`;
- `Trigger`;
- `TriggerEvent`;
- `WorkflowDefinition`;
- `WorkflowExecution`;
- `ExecutionContext`;
- `Capability`;
- `CapabilityProvider`;
- `Policy`; and
- `Publisher`.

The domain model and the responsibilities represented by these concepts remain
stable. Implementations, adapters, and other technical details may evolve without
changing those architectural boundaries.

`WorkflowExecution` remains the Runtime Aggregate Root as established by
[ADR-001](001-workflow-execution-aggregate-root.md).

The single explicit exception is `CapabilityResolver`. Its design remains
intentionally undecided until Agent Kit integration is fully understood.
`CapabilityResolver` is the only architectural component still under evaluation.

## Consequences

- Runtime implementation can advance against stable domain boundaries.
- Architectural changes require an explicit decision rather than emerging from
  implementation details.
- Adapters and infrastructure may evolve independently of the stable domain model.
- Work involving `CapabilityResolver` must avoid treating an interim design as a
  settled architectural decision.
- No other established Runtime concept is reopened by the `CapabilityResolver`
  exception.

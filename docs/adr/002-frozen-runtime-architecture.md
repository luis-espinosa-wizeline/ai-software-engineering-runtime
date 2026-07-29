# ADR-002 — Frozen Runtime Architecture

## Status

Accepted

Validated by Epics 8.5–9

## Context

The Runtime is responsible for deterministic workflow execution.

As Engineering capabilities evolve, new requirements will inevitably emerge. The primary architectural concern is preventing business responsibilities from leaking into the Runtime.

A stable execution core should evolve only when a workflow requires genuinely new execution semantics.

## Decision

The Runtime architecture is considered frozen.

Its responsibilities are limited to:

- Workflow discovery
- Workflow planning
- Deterministic execution
- Execution Patterns
- Artifact routing
- Execution Context management
- Capability resolution

Business logic belongs exclusively to Capabilities.

Engineering concepts belong exclusively to Artifacts.

The Runtime must evolve only when a workflow demonstrates the need for a fundamentally new execution semantic (for example, Iteration, Parallel Execution, Conditional Execution, or Retry).

## Validation

This decision was validated during the implementation of the first end-to-end Engineering Workflow.

The following evolution occurred:

- Epic 8.5 introduced the Iteration execution pattern.
- Epic 8.6 introduced Engineering Knowledge Aggregation as a Capability.
- Epic 8.7 evolved the EngineeringFinding domain model to preserve provenance.
- Epic 9 composed the complete Engineering workflow.

After Iteration was introduced, no additional Runtime responsibilities were required.

Subsequent epics extended:

- Capabilities,
- Artifacts,
- Workflow definitions,
- Documentation,
- Integration tests,

without modifying the Execution Engine, Planner, Artifact routing, or Capability contracts.

This demonstrates that execution semantics and Engineering semantics are correctly separated.

## Consequences

Future development should default to:

- new Capabilities,
- richer Artifacts,
- additional Workflows.

The Runtime should evolve only when new orchestration semantics are required.

Execution semantics should never be extended simply to accommodate business behavior.
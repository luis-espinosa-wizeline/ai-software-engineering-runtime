# ADR-003: Technology-Agnostic Domain Model

## Status

Accepted

## Context

The Runtime coordinates workflows that may be initiated, executed, and published
through different technologies. If domain concepts depend directly on a specific
provider, framework, persistence mechanism, or protocol, those concepts become
difficult to reuse and test outside that technology.

Infrastructure choices are expected to change more frequently than the stable
Runtime concepts documented in [ADR-002](002-frozen-runtime-architecture.md).

## Decision

The Runtime domain remains independent from infrastructure. Domain models must not
depend on:

- GitHub;
- FastAPI;
- OpenAI;
- Ollama;
- Agent Kit;
- databases; or
- transport protocols.

These technologies belong in adapters and infrastructure layers. They may translate
between external representations and the Runtime domain, but they do not define the
domain model.

The `WorkflowExecution` aggregate described in
[ADR-001](001-workflow-execution-aggregate-root.md) follows the same rule: it owns
execution state without depending on how that state is transported, stored, or
fulfilled.

## Consequences

- Domain models can be used with different triggers, providers, publishers, and
  transports.
- Domain behavior can be tested without external systems or framework setup.
- Infrastructure can be replaced or upgraded with limited impact on the domain.
- Adapters must translate technology-specific data into domain concepts.
- Technology-specific fields and types must not leak into Runtime domain models,
  even when doing so would simplify one integration.

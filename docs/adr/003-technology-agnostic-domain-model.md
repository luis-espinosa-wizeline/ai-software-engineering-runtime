# ADR-003 — Technology Agnostic Domain Model

## Status

Accepted

Validated by Epic 9

## Context

Engineering knowledge should remain independent from providers, transport mechanisms, and execution infrastructure.

The Runtime should operate on stable Engineering concepts rather than provider-specific representations.

## Decision

Engineering information shall be represented through technology-agnostic Artifacts.

Artifacts represent Engineering concepts rather than implementation details.

Examples include:

- SourceCode
- EngineeringFinding
- MarkdownDocument
- PublicationResult

Capabilities transform one Engineering Artifact into another.

The Runtime transports Artifacts but never interprets their Engineering meaning.

## Validation

The first end-to-end Engineering Workflow validated this decision.

Engineering knowledge successfully evolved through the following transformations:

Pull Request Event

↓

Changed Files

↓

SourceCode

↓

EngineeringFinding

↓

Merged Engineering Findings

↓

MarkdownDocument

↓

GitHub Comment

Throughout this workflow:

- provider implementations remained isolated,
- provenance was preserved,
- no Runtime changes were required,
- Artifacts remained independent from GitHub, Ollama, or any execution technology.

The Runtime transported Artifacts without understanding their Engineering semantics.

## Consequences

New providers should integrate by implementing Capabilities rather than introducing new Runtime abstractions.

Engineering concepts should evolve through Artifact contracts instead of provider-specific models.
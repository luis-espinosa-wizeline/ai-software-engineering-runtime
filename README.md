# AI Software Engineering Runtime

The AI Software Engineering Runtime is an execution platform for operationalizing AI capabilities across the software development lifecycle.

The Runtime owns event handling, workflow orchestration, repository context, policy evaluation, safe execution, and publishing results. AI providers supply capabilities; the Runtime decides when and how those capabilities are used.

## Problem

AI-assisted engineering often starts as provider-specific scripts or single-purpose automation. That works for experiments, but it becomes difficult to maintain when teams need repeatable workflows, consistent policy enforcement, reliable repository context, and auditable publishing back into developer systems.

This project separates the product runtime from AI providers and workflow implementations so new capabilities can be introduced without coupling every workflow to every provider.

## Core Concepts

- **Trigger**: An external event that starts runtime work. The first planned trigger is GitHub.
- **Workflow**: A product-level process executed by the Runtime. The first planned workflow is Code Review.
- **Capability**: An abstract AI-powered operation a workflow may request, such as reviewing code or summarizing changes.
- **Provider**: An implementation that fulfills capabilities without knowing which workflow requested them.
- **Policy**: Rules that constrain what the Runtime may do.
- **Context**: Repository, event, and workflow data prepared for execution.
- **Execution**: The controlled environment and process used to perform work.
- **Publisher**: A boundary responsible for delivering results to external systems.

## Current MVP

The current foundation contains:

- A minimal FastAPI application.
- Explicit package boundaries for runtime, workflows, capabilities, providers, GitHub, policy, context, execution, publishing, and shared code.
- Project metadata for Python 3.14, Pydantic v2, httpx, pytest, ruff, and mypy.
- Architecture documentation for the initial runtime model.

The only HTTP endpoint is:

```http
GET /
```

It returns:

```json
{
  "name": "AI Software Engineering Runtime",
  "version": "0.1.0"
}
```

## High-Level Architecture

The Runtime is intentionally organized around boundaries rather than provider-specific features.

- `app/api`: FastAPI entrypoints and HTTP transport concerns.
- `app/runtime`: Runtime coordination concepts.
- `app/workflows`: Workflow definitions and workflow-specific orchestration.
- `app/capabilities`: Capability contracts and resolution concepts.
- `app/providers`: Provider implementations.
- `app/github`: GitHub trigger and publishing integration.
- `app/policy`: Policy evaluation.
- `app/context`: Repository and event context preparation.
- `app/execution`: Safe execution primitives.
- `app/publishing`: Result publication boundaries.
- `app/shared`: Cross-cutting types and helpers.

FastAPI should remain at the edge. Domain and workflow code should stay framework-independent.

## Roadmap

- GitHub webhook trigger.
- Code Review workflow.
- Capability resolution.
- Provider integration.
- Repository context assembly.
- Policy evaluation.
- Safe execution controls.
- GitHub result publishing.
- Additional workflows such as bug fixing, feature development, documentation, incident response, and architecture analysis.

## Project Status

This repository is at foundation stage. It does not yet implement the workflow engine, provider integrations, GitHub integration, policy logic, execution sandboxing, or publishing behavior.

## Development Setup

Install dependencies:

```bash
uv sync
```

Run the application:

```bash
uv run fastapi dev app/main.py
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Run type checking:

```bash
uv run mypy app tests
```


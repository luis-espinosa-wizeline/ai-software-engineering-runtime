# Runtime Overview

## Mission

Provide a reliable execution platform for AI-assisted software engineering workflows.

## Vision

The Runtime should make AI capabilities operational across the software development lifecycle while keeping workflow logic, provider implementations, infrastructure, policy, context, execution, and publishing concerns separate.

AI providers provide capabilities. The Runtime executes workflows.

## Core Concepts

### Trigger

A trigger is an external event that starts runtime work. The first supported trigger will be GitHub.

### Workflow

A workflow is a product-level process coordinated by the Runtime. The first supported workflow will be Code Review.

### Capability

A capability is an abstract operation a workflow can request without depending on a provider implementation.

### Provider

A provider implements one or more capabilities. Providers do not know which workflow requested the capability.

### Policy

Policy defines rules that constrain runtime behavior before, during, and after execution.

### Context

Context is the repository, event, and workflow data prepared for a workflow execution.

### Execution

Execution is the controlled process and environment used to perform workflow work safely and repeatably.

### Publisher

A publisher delivers workflow results to external systems such as GitHub.

## Component Diagram

```mermaid
flowchart TD
    github_trigger[GitHub Trigger]
    workflow_engine[Workflow Engine]
    workflow[Workflow]
    capability_resolver[Capability Resolver]
    capability_provider[Capability Provider]
    publisher[Publisher]

    github_trigger --> workflow_engine
    workflow_engine --> workflow
    workflow --> capability_resolver
    capability_resolver --> capability_provider
    capability_provider --> publisher
```

## Current Scope

This repository currently contains only the foundation for the Runtime. It intentionally does not implement the workflow engine, capability provider contracts, GitHub integration, policy logic, execution sandboxing, or publishing behavior yet.


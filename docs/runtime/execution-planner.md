# Execution Planner

## Responsibility

The `ExecutionPlanner` transforms a `WorkflowDefinition` into an immutable,
reusable `ExecutionPlan`. It validates declarative workflow semantics, resolves
internal references, preserves declared step order and action contracts, and
constructs a plan that satisfies the Execution Plan domain rules.

```text
WorkflowDefinition
        |
        v
ExecutionPlanner
        |
        v
ExecutionPlan
```

The three stages represent different architectural concerns:

- `WorkflowDefinition` is declarative intent.
- `ExecutionPlanner` is deterministic planning.
- `ExecutionPlan` is the immutable, provider-neutral input to later execution
  behavior.

The planner does not execute the plan or modify the workflow definition.

## Deterministic Planning

Planning is deterministic: the same workflow definition always produces the same
plan. The planner reads only declarative workflow data, preserves its declared
order, and does not consult providers, runtime configuration, execution context,
or external state.

The planner behaves conceptually like a compiler. A workflow definition is its
declarative source; the planner validates workflow semantics, resolves declarative
references, and produces an immutable execution plan. Semantic validation rejects
invalid references and dependency structures before execution begins.

This compiler analogy is deliberately limited. The planner does not optimize the
workflow, infer behavior that was not declared, select providers, or execute
capabilities.

## Separation of Responsibilities

- **WorkflowDefinition** expresses reusable workflow intent: structurally typed
  input definitions, ordered steps, action contracts, bindings, outputs, and
  the intended result. It remains a declarative model and does not express
  execution behavior.
- **ExecutionPlanner** validates that intent and translates it into an execution
  strategy.
- **ExecutionPlan** is the immutable, provider-neutral strategy produced by
  planning.
- **ExecutionEngine** will coordinate a valid plan. It is not part of planning
  and is not implemented by this component.

## Semantic Validation

Before constructing a plan, the planner verifies that:

- the workflow has steps and a result;
- step identifiers, declared inputs, step outputs, and binding parameters are
  unambiguous;
- optional inputs are not bound to steps until defaults or conditional
  execution provide an explicit absence semantic;
- every step declares an action contract;
- bindings refer to declared workflow inputs or outputs from known steps;
- referenced outputs exist;
- dependencies are acyclic and respect declared execution order;
- every step contributes to the declared workflow result; and
- the result refers to a declared step output.

Failures distinguish an incomplete or structurally invalid workflow, invalid
workflow semantics, and failure to construct the Execution Plan domain model.

## Workflow Reachability

Every workflow step must contribute to the declared workflow result through the
dependency graph. A step is valid when the result depends on its output, either
directly or through other steps. Disconnected and dead steps are rejected during
planning.

This is an intentional constraint of the current execution model: a workflow
definition describes only the work needed to produce its declared result. A
future Runtime may support explicitly declared effect-only steps for auditing,
telemetry, notifications, or logging. Such steps are intentionally outside the
current model and are not inferred or accepted by the planner.

## Action Contracts and Required Capabilities

An action contract is the provider-neutral operation a workflow step intends to
perform: it describes what should happen. A required capability instead describes
a capability or prerequisite needed by a workflow or step. It does not identify
the executable operation itself.

The planner does not resolve capabilities. It preserves each declared action
contract as it produces the corresponding plan step. Capability resolution
belongs to later Runtime components.

## Provider Independence

The planner copies action-contract identifiers without resolving them. It does
not perform capability lookup, select providers or AI models, or inspect runtime
configuration. Those concerns depend on operational choices and belong after
deterministic planning.

## Evolution of the Workflow Model

The Foundation workflow models originally described steps and capabilities but
did not contain enough declarative information to produce an execution plan.
They evolved minimally to include typed required inputs, action contracts, input
bindings, declared outputs, and a workflow result reference.

These fields express workflow intent; they do not introduce execution behavior
into the definition. Workflow definitions intentionally do not contain providers,
runtime configuration, retries, execution status, execution context, execution
data, or policy decisions. Those concerns belong to later Runtime components.

Core planning semantics were deliberately not placed in `metadata`: metadata is
untyped, cannot make references explicit, and would move essential validation
from the domain boundary into an implicit planner-specific convention.

The workflow types remain distinct from execution-plan types. The planner owns
their transformation, preserving the architectural boundary between intent and
execution strategy.

# Runtime Host SPI

The Runtime Host SPI is the provider-neutral application boundary that turns a
normalized external event into one invocation of the existing Runtime Execution
Core. It makes the assembly demonstrated by the first Engineering Workflow
reusable without adding hosting concerns to planning or execution.

```text
External adapter
        |
        v
HostEvent
        |
        v
WorkflowSelector
        |
        v
RuntimeHost
        |-- ProjectLoader / WorkflowRegistry
        |-- WorkflowInputValidator
        |-- CapabilityComposition
        |-- ExecutionPlanner
        |-- ExecutionContextFactory
        `-- ExecutionEngine
        |
        v
HostExecutionResult
```

## Contracts

- `HostEvent` contains an event kind, provider-neutral workflow inputs, and
  optional correlation-safe identifiers and metadata. It contains no
  credentials, clients, or intermediate Artifacts.
- `WorkflowRoute` identifies one workflow ID and exact version.
- `WorkflowSelector` maps an event to a route without inspecting workflow
  steps. `InMemoryWorkflowSelector` provides explicit event-kind routing.
- `WorkflowInputValidator` strictly validates normalized values against the
  selected Workflow's structural input contract without coercion.
- `CapabilityComposition` produces the `CapabilityResolver` configured for one
  execution. `InMemoryCapabilityComposition` supports explicit assembly without
  plugin loading or a dependency-injection framework.
- `ExecutionContextFactory` creates a fresh context with a new execution ID,
  plan ID, and normalized inputs. It never seeds step Artifacts.
- `RuntimeHost` coordinates selection and assembly, then delegates execution.
- `HostExecutionResult` reports execution identity, workflow identity, success,
  and the Runtime's final Artifact without adapting it to a transport.

## Execution sequence

For every event, `RuntimeHost.execute` performs exactly this sequence:

1. select a `WorkflowRoute`;
2. load the project and retrieve the exact `WorkflowDefinition`;
3. validate `HostEvent.inputs` against the selected Workflow;
4. obtain a `CapabilityResolver` from `CapabilityComposition`;
5. compile the definition with `ExecutionPlanner`;
6. create a fresh `ExecutionContext` from the validated inputs;
7. construct and invoke `ExecutionEngine` exactly once; and
8. return the final Artifact in `HostExecutionResult`.

The Host does not inspect steps, resolve bindings, invoke Capabilities, route
intermediate Artifacts, implement iteration, or transform Engineering values.
Those remain responsibilities of the existing Execution Core and Capability
ecosystem.

Invalid inputs stop before capability composition and execution. See
[Workflow Input Contracts](workflow-input-contracts.md).

## Dependency direction

`app.host` depends inward on project discovery, workflow cataloging, planning,
context, capability resolution, and execution. None of those packages imports
or depends on `app.host`.

Provider-specific adapters sit outside the Host SPI:

```text
GitHub / REST / CLI / queue / IDE
        |
        v
provider-specific normalization and configuration
        |
        v
provider-neutral Host SPI
        |
        v
Runtime Execution Core
```

A future GitHub adapter can verify a webhook, normalize repository and
pull-request inputs, configure GitHub and analysis implementations through
`CapabilityComposition`, and call the same `RuntimeHost`.

REST, CLI, worker, and IDE adapters can normalize their own inputs and reuse the
same contracts. Transport acknowledgements, queue delivery behavior, UI
responses, credentials, and provider configuration remain outside the SPI.

## Agent Kit boundary

Agent Kit Skills are not implemented in this epic. A future Agent Kit adapter
may implement an existing Capability contract, or be wrapped by a
`CapabilityImplementation` assembled through `CapabilityComposition`.

The `ExecutionEngine` continues to see only the provider-neutral Capability
execution contract and must never gain direct knowledge of Agent Kit.

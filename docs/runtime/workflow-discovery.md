# Workflow Discovery and Registry

## Discovery

`WorkflowDiscovery` is the boundary for locating workflow definitions. Its only
operation returns a collection of `WorkflowDefinition` values. The initial
`InMemoryWorkflowDiscovery` implementation snapshots an iterable supplied by the
caller; it performs no imports, reflection, filesystem access, plugin loading, or
execution.

Future discovery mechanisms can implement the same protocol without changing the
registry or its query API.

## Registry

`WorkflowRegistry` builds a validated catalog from an iterable or a
`WorkflowDiscovery`. Construction snapshots and sorts the definitions. The
registry and every collection returned from it are immutable; definitions are
returned unchanged and are never mutated by the registry.

An empty registry is valid. It represents a Runtime in which discovery found no
workflows and makes list and existence queries useful during incremental
configuration.

Catalog order is deterministic: workflow id first, then the opaque version
string, both in ascending lexical order.

## Validation

A workflow identity is the pair `(workflow_id, version)`. The registry rejects:

- duplicate workflow identities;
- more than one active version for a workflow id;
- non-boolean `active` or `enabled` registry metadata; and
- `triggers` metadata that is not a list of non-empty strings.

Identifier validation remains the responsibility of the current domain models.
The registry does not add identifier rules that the domain has not defined.

Registry-specific failures derive from `WorkflowRegistryError`:
`DuplicateWorkflow`, `WorkflowNotFound`, `AmbiguousActiveWorkflow`, and
`InvalidWorkflowDefinition`.

## Version resolution

Versions are opaque strings. The registry never parses, compares, or infers
semantic versions. A definition opts into active resolution with
`metadata["active"] = true`. At most one version per workflow id may be active.

`get(workflow_id)` returns the active definition. `get(workflow_id, version)`
performs an exact version lookup, and `active_version(workflow_id)` returns the
active definition's version string. Missing workflows, versions, and active
versions raise `WorkflowNotFound`.

The registry metadata contract is:

- `active`: boolean, default `false`;
- `enabled`: boolean, default `true`; and
- `triggers`: list of non-empty trigger names or kinds, default empty.

`list()`, `list_enabled()`, and `list_by_trigger(trigger)` return immutable tuples
in catalog order. `exists(workflow_id)` checks whether any version exists.
Trigger matching is exact and case-sensitive.

## Future extension points

Filesystem, module, decorator, and plugin discovery can be introduced as new
`WorkflowDiscovery` implementations. They must still produce domain
`WorkflowDefinition` values. Registry validation, ordering, version resolution,
and queries remain independent of how definitions were located.

The registry does not execute workflows, invoke capabilities, resolve providers,
or contact infrastructure.

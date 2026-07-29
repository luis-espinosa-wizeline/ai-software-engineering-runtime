# Workflow Input Contracts

A Workflow declares the structural contract of the external values required to
start it. The contract is provider-neutral and is validated by the Runtime Host
after workflow selection and before capability composition, planning, context
creation, or execution.

## Model

Each immutable `WorkflowInputDefinition` contains:

- `name`;
- `type`; and
- `required`, defaulting to `true`.

The supported structural types are:

- `string`;
- `integer`;
- `boolean`;
- `number`;
- `object`; and
- `array`.

The model deliberately excludes unions, nested schemas, references, provider
classes, and Engineering Artifact types.

## Strict validation

`WorkflowInputValidator` rejects:

- missing required inputs;
- undeclared inputs;
- values with the wrong structural type; and
- `null` for any supplied input.

Validation performs no coercion. `"42"` is not an integer. Python booleans are
not integers or numbers for this contract. Integers are accepted as numbers,
which follows the usual structural relationship while still excluding
booleans.

The validator returns a copied, validated mapping. That mapping is the only
external input data used to create the `ExecutionContext`.

Optional inputs may be omitted. Until workflow defaults or conditional
execution exist, the planner rejects binding an optional input to a step; this
prevents an omitted value from failing later during execution.

## Responsibility split

Workflow input validation covers invocation structure only:

- declared names;
- required presence;
- primitive structural types; and
- unexpected values.

Capabilities retain Engineering and provider semantics, such as whether a
repository or pull request exists, whether credentials are authorized, whether
an API response is valid, what source code means, and how a model behaves.

The Execution Engine receives an already selected Workflow and a context built
from validated inputs. It does not parse external events or validate provider
payloads.

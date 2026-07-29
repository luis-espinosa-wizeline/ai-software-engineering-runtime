"""Fresh execution-context creation at the Runtime Host boundary."""

from collections.abc import Callable, Mapping
from uuid import uuid4

from app.execution import ExecutionContext, ExecutionPlan
from app.shared import JsonValue, RuntimeId


class ExecutionContextFactory:
    """Create an empty per-execution context for an existing plan."""

    def __init__(self, execution_id_factory: Callable[[], RuntimeId] = uuid4) -> None:
        self._execution_id_factory = execution_id_factory

    def create(
        self,
        plan: ExecutionPlan,
        inputs: Mapping[str, JsonValue],
    ) -> ExecutionContext:
        """Create a fresh context containing workflow inputs and no step Artifacts."""
        return ExecutionContext(
            execution_id=self._execution_id_factory(),
            plan_id=plan.plan_id,
            inputs=dict(inputs),
        )

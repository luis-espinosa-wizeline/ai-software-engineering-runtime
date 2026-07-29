"""Provider-neutral coordination from an external event to Runtime execution."""

from collections.abc import Callable
from pathlib import Path

from app.capabilities import CapabilityResolver
from app.execution import ExecutionEngine, ExecutionPlanner
from app.host.composition import CapabilityComposition
from app.host.context import ExecutionContextFactory
from app.host.events import HostEvent
from app.host.results import HostExecutionResult
from app.host.routing import WorkflowSelector
from app.project import ProjectLoader
from app.workflows import WorkflowInputValidator, WorkflowRegistry

type ExecutionEngineFactory = Callable[[CapabilityResolver], ExecutionEngine]


class RuntimeHost:
    """Prepare and delegate one normalized event to the Runtime Execution Core."""

    def __init__(
        self,
        project_root: str | Path,
        workflow_selector: WorkflowSelector,
        capability_composition: CapabilityComposition,
        *,
        project_loader: ProjectLoader | None = None,
        planner: ExecutionPlanner | None = None,
        context_factory: ExecutionContextFactory | None = None,
        input_validator: WorkflowInputValidator | None = None,
        engine_factory: ExecutionEngineFactory = ExecutionEngine,
    ) -> None:
        self._project_root = Path(project_root)
        self._workflow_selector = workflow_selector
        self._capability_composition = capability_composition
        self._project_loader = project_loader or ProjectLoader()
        self._planner = planner or ExecutionPlanner()
        self._context_factory = context_factory or ExecutionContextFactory()
        self._input_validator = input_validator or WorkflowInputValidator()
        self._engine_factory = engine_factory

    def execute(self, event: HostEvent) -> HostExecutionResult:
        """Select, prepare, and execute one workflow through the existing engine."""
        route = self._workflow_selector.select(event)
        project = self._project_loader.load(self._project_root)
        workflow = WorkflowRegistry(project.workflows).get(
            route.workflow_id,
            route.workflow_version,
        )
        validated_inputs = self._input_validator.validate(workflow, event.inputs)
        resolver = self._capability_composition.compose(event, workflow)
        plan = self._planner.plan(workflow)
        context = self._context_factory.create(plan, validated_inputs)
        final_artifact = self._engine_factory(resolver).execute(plan, context)
        return HostExecutionResult(
            execution_id=context.execution_id,
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            success=True,
            final_artifact=final_artifact,
        )

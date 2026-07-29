"""Production GitHub adapter for the provider-neutral Runtime Host SPI."""

from collections.abc import Callable

from app.github.authentication import GitHubAppAuthenticator
from app.github.composition import GitHubCapabilityComposition
from app.github.config import GitHubHostSettings
from app.github.webhook import (
    GitHubPullRequestEvent,
    GitHubWebhookVerifier,
    parse_pull_request_event,
)
from app.github.workspace import RepositoryWorkspace, WorkspaceManager
from app.host import (
    CapabilityComposition,
    HostEvent,
    HostExecutionResult,
    InMemoryWorkflowSelector,
    RuntimeHost,
    WorkflowRoute,
)

GITHUB_PULL_REQUEST_EVENT_KIND = "github.pull_request"
type GitHubCompositionFactory = Callable[
    [GitHubPullRequestEvent, str, RepositoryWorkspace, GitHubHostSettings],
    CapabilityComposition,
]
PULL_REQUEST_WORKFLOW = WorkflowRoute(
    workflow_id="pull-request-engineering-review",
    workflow_version="1",
)


class GitHubRuntimeHost:
    """Verify, prepare, and delegate a GitHub event to the Runtime Host SPI."""

    def __init__(
        self,
        settings: GitHubHostSettings,
        *,
        authenticator: GitHubAppAuthenticator | None = None,
        workspace_manager: WorkspaceManager | None = None,
        verifier: GitHubWebhookVerifier | None = None,
        composition_factory: GitHubCompositionFactory | None = None,
    ) -> None:
        self._settings = settings
        self._authenticator = authenticator or GitHubAppAuthenticator(
            app_id=settings.github_app_id,
            private_key=settings.github_private_key,
            api_url=settings.github_api_url,
        )
        self._workspace_manager = workspace_manager or WorkspaceManager(
            base_directory=settings.workspace_base,
            max_file_bytes=settings.workspace_max_file_bytes,
            allowed_clone_hosts=frozenset({settings.github_clone_host}),
        )
        self._verifier = verifier or GitHubWebhookVerifier(
            settings.github_webhook_secret
        )
        self._composition_factory = (
            composition_factory or self._default_composition
        )

    def handle(
        self,
        *,
        body: bytes,
        signature: str | None,
        event_name: str | None,
        delivery_id: str | None,
    ) -> HostExecutionResult:
        """Execute one supported, authentic GitHub pull-request delivery."""
        self._verifier.verify(body, signature)
        event = parse_pull_request_event(
            event_name=event_name,
            delivery_id=delivery_id,
            body=body,
        )
        token = self._authenticator.installation_token(event.installation_id)
        with self._workspace_manager.prepare(
            clone_url=event.clone_url,
            commit_sha=event.head_sha,
            token=token,
        ) as workspace:
            composition = self._composition_factory(
                event,
                token,
                workspace,
                self._settings,
            )
            host = RuntimeHost(
                self._settings.project_root,
                InMemoryWorkflowSelector(
                    {GITHUB_PULL_REQUEST_EVENT_KIND: PULL_REQUEST_WORKFLOW}
                ),
                composition,
            )
            return host.execute(
                HostEvent(
                    event_kind=GITHUB_PULL_REQUEST_EVENT_KIND,
                    event_id=event.delivery_id,
                    inputs={
                        "repository": event.repository,
                        "pull_request_number": event.pull_request_number,
                    },
                    metadata={"action": event.action},
                )
            )

    @staticmethod
    def _default_composition(
        event: GitHubPullRequestEvent,
        token: str,
        workspace: RepositoryWorkspace,
        settings: GitHubHostSettings,
    ) -> CapabilityComposition:
        return GitHubCapabilityComposition(
            repository=event.repository,
            pull_request_number=event.pull_request_number,
            installation_token=token,
            workspace=workspace,
            ollama_model=settings.ollama_model,
            github_api_url=settings.github_api_url,
            ollama_base_url=settings.ollama_base_url,
        )


def build_github_runtime_host() -> GitHubRuntimeHost:
    """Build the production GitHub Host from environment configuration."""
    return GitHubRuntimeHost(GitHubHostSettings.from_environment())

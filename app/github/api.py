"""FastAPI transport for GitHub Runtime Host webhook deliveries."""

from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from app.github.errors import (
    GitHubHostError,
    InvalidGitHubEvent,
    InvalidWebhookSignature,
    UnsupportedGitHubEvent,
)
from app.github.host import GitHubRuntimeHost, build_github_runtime_host

router = APIRouter(prefix="/github", tags=["github"])


class GitHubWebhookResponse(BaseModel):
    """Transport response containing no provider credentials or Runtime internals."""

    model_config = ConfigDict(frozen=True)

    accepted: bool
    execution_id: str
    workflow_id: str
    workflow_version: str
    result_artifact: str


def _host(request: Request) -> GitHubRuntimeHost:
    configured = getattr(request.app.state, "github_runtime_host", None)
    if configured is None:
        configured = build_github_runtime_host()
        request.app.state.github_runtime_host = configured
    return cast(GitHubRuntimeHost, configured)


@router.post(
    "/webhooks",
    response_model=GitHubWebhookResponse,
    status_code=status.HTTP_200_OK,
)
async def receive_github_webhook(request: Request) -> GitHubWebhookResponse:
    """Verify and synchronously execute one supported GitHub webhook."""
    body = await request.body()
    try:
        result = await run_in_threadpool(
            _host(request).handle,
            body=body,
            signature=request.headers.get("X-Hub-Signature-256"),
            event_name=request.headers.get("X-GitHub-Event"),
            delivery_id=request.headers.get("X-GitHub-Delivery"),
        )
    except InvalidWebhookSignature as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except (UnsupportedGitHubEvent, InvalidGitHubEvent) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except GitHubHostError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return GitHubWebhookResponse(
        accepted=True,
        execution_id=str(result.execution_id),
        workflow_id=result.workflow_id,
        workflow_version=result.workflow_version,
        result_artifact=result.final_artifact.name,
    )

# GitHub Runtime Host

The GitHub Runtime Host is the first production adapter for the
provider-neutral Runtime Host SPI. It accepts authenticated GitHub pull-request
deliveries and prepares the infrastructure required by the existing
`pull-request-engineering-review` Workflow.

```text
GitHub pull-request webhook
        |
        v
HMAC-SHA256 verification
        |
        v
GitHub App installation token
        |
        v
exact-SHA temporary workspace
        |
        v
GitHubCapabilityComposition
        |
        v
RuntimeHost.execute
        |
        v
publication_result
```

## Webhook boundary

`POST /github/webhooks` verifies `X-Hub-Signature-256` against the exact request
body before parsing it. The initial Host accepts `pull_request` events with
`opened`, `reopened`, or `synchronize` actions.

The adapter normalizes only the workflow inputs:

- `repository`, as `owner/name`; and
- `pull_request_number`, as an integer.

GitHub delivery and action values are correlation metadata. Authentication
tokens, clone URLs, workspaces, API clients, and provider responses never enter
`HostEvent.inputs`, `ExecutionContext`, or Engineering Artifacts.

## GitHub App authentication

`GitHubAppAuthenticator` creates a short-lived RS256 application JWT and
exchanges it for a token scoped to the webhook's installation ID. The token is
used only to:

- fetch the exact repository revision;
- read pull-request changed-file data; and
- publish the final Markdown comment.

The Runtime and Workflow remain unaware of authentication.

## Immutable workspace

`WorkspaceManager` allocates an isolated temporary directory and fetches the
full pull-request head SHA with depth one. Preparation disables interactive
prompts, repository hooks, file-protocol access, and recursive submodules.

The workspace is removed after successful execution, preparation failure, or
execution failure.

Capabilities exchange repository-relative logical paths. The workspace reader:

- rejects absolute and parent-traversal paths;
- resolves symlinks and rejects workspace escape;
- requires regular files;
- enforces a configured size limit; and
- reads strict UTF-8.

Removed files are excluded because they do not exist in the head snapshot. This
initial Workflow analyzes readable head-state files; analysis of deletions
requires a future explicit base/head domain contract.

## Execution-scoped composition

`GitHubCapabilityComposition` assembles:

- `GitHubRepositoryReader` with `ReadChangedFilesImplementation`;
- a workspace-confined `ReadFileImplementation`;
- `AnalyzeSourceCodeOllamaImplementation`;
- `MergeEngineeringFindingsImplementation`;
- `GenerateMarkdownImplementation`; and
- the existing `GitHubCommentPublisher` behind
  `PublishGitHubCommentImplementation`.

It produces the existing `InMemoryCapabilityResolver`. It does not execute
Capabilities or inspect workflow steps.

## Configuration

The Host loads infrastructure configuration from:

| Environment variable | Required | Purpose |
|---|---:|---|
| `GITHUB_APP_ID` | yes | GitHub App identity |
| `GITHUB_PRIVATE_KEY` | yes | PEM private key; escaped newlines are accepted |
| `GITHUB_WEBHOOK_SECRET` | yes | webhook HMAC secret |
| `OLLAMA_MODEL` | yes | analysis model |
| `RUNTIME_PROJECT_ROOT` | no | project containing `runtime.yaml`; defaults to `.` |
| `GITHUB_API_URL` | no | GitHub API base URL |
| `GITHUB_CLONE_HOST` | no | permitted Git clone host; defaults to `github.com` |
| `OLLAMA_BASE_URL` | no | Ollama base URL |
| `RUNTIME_WORKSPACE_BASE` | no | parent directory for isolated workspaces |
| `RUNTIME_WORKSPACE_MAX_FILE_BYTES` | no | per-file read limit; defaults to 1 MB |

The endpoint currently executes synchronously from the delivery's perspective,
while moving blocking work off the application event loop. Large production
installations may later acknowledge into a durable worker, but queueing and
retry orchestration are not part of this epic.

The workspace sends installation credentials only to the explicitly configured
clone host and rejects URLs containing embedded credentials.

## Runtime isolation

No Execution Core package imports `app.github`. The GitHub Host uses the public
Host SPI and existing Capability contracts. Planning, binding resolution,
iteration, Artifact routing, and workflow execution remain unchanged.

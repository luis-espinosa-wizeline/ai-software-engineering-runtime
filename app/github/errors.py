"""Failures confined to the GitHub Runtime Host boundary."""


class GitHubHostError(Exception):
    """Base error for GitHub Host failures."""


class InvalidWebhookSignature(GitHubHostError):
    """Raised when a webhook signature is absent or invalid."""


class UnsupportedGitHubEvent(GitHubHostError):
    """Raised when a webhook is not a supported pull-request event."""


class InvalidGitHubEvent(GitHubHostError):
    """Raised when a webhook payload lacks required execution data."""


class GitHubAuthenticationError(GitHubHostError):
    """Raised when GitHub App authentication cannot produce a token."""


class GitHubApiError(GitHubHostError):
    """Raised when GitHub repository API access fails."""


class WorkspacePreparationError(GitHubHostError):
    """Raised when an immutable repository workspace cannot be prepared."""


class UnsafeWorkspacePath(GitHubHostError):
    """Raised when a repository path escapes or violates the workspace policy."""

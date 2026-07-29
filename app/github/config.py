"""Environment-backed configuration for the GitHub Runtime Host."""

import os
from pathlib import Path

from pydantic import Field, model_validator

from app.shared import DomainModel


class GitHubHostSettings(DomainModel):
    """Infrastructure configuration kept outside Runtime inputs and Artifacts."""

    github_app_id: str
    github_private_key: str
    github_webhook_secret: str
    ollama_model: str
    project_root: Path
    github_api_url: str = "https://api.github.com"
    github_clone_host: str = "github.com"
    ollama_base_url: str = "http://localhost:11434"
    workspace_base: Path | None = None
    workspace_max_file_bytes: int = Field(default=1_000_000, ge=1)

    @model_validator(mode="after")
    def _validate_strings(self) -> GitHubHostSettings:
        for field_name in (
            "github_app_id",
            "github_private_key",
            "github_webhook_secret",
            "ollama_model",
            "github_api_url",
            "github_clone_host",
            "ollama_base_url",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be blank")
        return self

    @classmethod
    def from_environment(cls) -> GitHubHostSettings:
        """Load required Host infrastructure configuration from environment."""
        return cls(
            github_app_id=os.environ["GITHUB_APP_ID"],
            github_private_key=os.environ["GITHUB_PRIVATE_KEY"].replace("\\n", "\n"),
            github_webhook_secret=os.environ["GITHUB_WEBHOOK_SECRET"],
            ollama_model=os.environ["OLLAMA_MODEL"],
            project_root=Path(os.environ.get("RUNTIME_PROJECT_ROOT", ".")).resolve(),
            github_api_url=os.environ.get(
                "GITHUB_API_URL",
                "https://api.github.com",
            ),
            github_clone_host=os.environ.get("GITHUB_CLONE_HOST", "github.com"),
            ollama_base_url=os.environ.get(
                "OLLAMA_BASE_URL",
                "http://localhost:11434",
            ),
            workspace_base=(
                Path(value).resolve()
                if (value := os.environ.get("RUNTIME_WORKSPACE_BASE"))
                else None
            ),
            workspace_max_file_bytes=int(
                os.environ.get("RUNTIME_WORKSPACE_MAX_FILE_BYTES", "1000000")
            ),
        )

"""Execution-scoped immutable repository workspace preparation."""

import base64
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from app.github.errors import UnsafeWorkspacePath, WorkspacePreparationError

_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
type CommandRunner = Callable[[list[str], Path, Mapping[str, str]], None]


class RepositoryWorkspace:
    """Confined immutable view of one checked-out repository revision."""

    def __init__(self, root: Path, commit_sha: str, max_file_bytes: int) -> None:
        self.root = root
        self.commit_sha = commit_sha
        self._max_file_bytes = max_file_bytes

    def read_text(self, path: Path) -> str:
        """Read a repository-relative UTF-8 file without permitting root escape."""
        logical = PurePosixPath(path.as_posix())
        if logical.is_absolute() or not logical.parts or ".." in logical.parts:
            raise UnsafeWorkspacePath(f"Unsafe repository path: {path}")
        try:
            candidate = (self.root / Path(*logical.parts)).resolve(strict=True)
            candidate.relative_to(self.root.resolve(strict=True))
        except (FileNotFoundError, ValueError) as error:
            raise UnsafeWorkspacePath(
                f"Repository path is missing or escapes the workspace: {path}"
            ) from error
        if not candidate.is_file():
            raise UnsafeWorkspacePath(f"Repository path is not a regular file: {path}")
        if candidate.stat().st_size > self._max_file_bytes:
            raise UnsafeWorkspacePath(f"Repository file exceeds the size limit: {path}")
        return candidate.read_text(encoding="utf-8")


class WorkspaceManager:
    """Allocate, prepare, and always remove isolated repository workspaces."""

    def __init__(
        self,
        *,
        base_directory: Path | None = None,
        max_file_bytes: int = 1_000_000,
        allowed_clone_hosts: frozenset[str] = frozenset({"github.com"}),
        command_runner: CommandRunner | None = None,
    ) -> None:
        if max_file_bytes < 1:
            raise ValueError("Workspace file-size limit must be positive")
        self._base_directory = base_directory
        self._max_file_bytes = max_file_bytes
        if not allowed_clone_hosts or any(
            not host.strip() for host in allowed_clone_hosts
        ):
            raise ValueError("Workspace clone hosts must not be empty")
        self._allowed_clone_hosts = allowed_clone_hosts
        self._command_runner = command_runner or self._run

    @contextmanager
    def prepare(
        self,
        *,
        clone_url: str,
        commit_sha: str,
        token: str,
    ) -> Iterator[RepositoryWorkspace]:
        """Yield an exact shallow checkout and guarantee recursive cleanup."""
        self._validate_source(clone_url, commit_sha, token)
        workspace = Path(
            tempfile.mkdtemp(
                prefix="runtime-workspace-",
                dir=self._base_directory,
            )
        )
        try:
            self._prepare_checkout(workspace, clone_url, commit_sha, token)
        except Exception as error:
            shutil.rmtree(workspace, ignore_errors=True)
            if isinstance(error, WorkspacePreparationError):
                raise
            raise WorkspacePreparationError(
                "Repository workspace could not be prepared"
            ) from error

        try:
            yield RepositoryWorkspace(
                workspace,
                commit_sha,
                self._max_file_bytes,
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _prepare_checkout(
        self,
        workspace: Path,
        clone_url: str,
        commit_sha: str,
        token: str,
    ) -> None:
        credentials = base64.b64encode(
            f"x-access-token:{token}".encode()
        ).decode()
        environment = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": "4",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {credentials}",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": os.devnull,
            "GIT_CONFIG_KEY_2": "protocol.file.allow",
            "GIT_CONFIG_VALUE_2": "never",
            "GIT_CONFIG_KEY_3": "submodule.recurse",
            "GIT_CONFIG_VALUE_3": "false",
        }
        commands = (
            ["git", "init", "--quiet"],
            ["git", "remote", "add", "origin", clone_url],
            ["git", "fetch", "--quiet", "--depth=1", "origin", commit_sha],
            ["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"],
        )
        for command in commands:
            self._command_runner(command, workspace, environment)

    def _validate_source(
        self,
        clone_url: str,
        commit_sha: str,
        token: str,
    ) -> None:
        parsed = urlparse(clone_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in self._allowed_clone_hosts
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise WorkspacePreparationError(
                "Repository clone URL must use HTTPS on an allowed host "
                "without embedded credentials"
            )
        if not _COMMIT_SHA.fullmatch(commit_sha):
            raise WorkspacePreparationError("Repository commit must be a full SHA")
        if not token:
            raise WorkspacePreparationError("Repository token must not be empty")

    @staticmethod
    def _run(
        command: list[str],
        workspace: Path,
        environment: Mapping[str, str],
    ) -> None:
        try:
            subprocess.run(
                command,
                cwd=workspace,
                env=environment,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise WorkspacePreparationError(
                f"Workspace command failed: {' '.join(command[:2])}"
            ) from error

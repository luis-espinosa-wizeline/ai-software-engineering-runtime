from collections.abc import Mapping
from pathlib import Path

import pytest

from app.github import (
    UnsafeWorkspacePath,
    WorkspaceManager,
    WorkspacePreparationError,
)

SHA = "a" * 40


def test_workspace_is_exactly_prepared_confined_and_always_removed(
    tmp_path: Path,
) -> None:
    commands: list[tuple[list[str], Path, Mapping[str, str]]] = []

    def run(
        command: list[str],
        workspace: Path,
        environment: Mapping[str, str],
    ) -> None:
        commands.append((command, workspace, environment))
        if command[:2] == ["git", "checkout"]:
            source = workspace / "src" / "service.py"
            source.parent.mkdir()
            source.write_text("VALUE = 1\n", encoding="utf-8")

    manager = WorkspaceManager(
        base_directory=tmp_path,
        max_file_bytes=100,
        command_runner=run,
    )

    with manager.prepare(
        clone_url="https://github.com/example/runtime.git",
        commit_sha=SHA,
        token="installation-token",
    ) as workspace:
        root = workspace.root
        assert workspace.commit_sha == SHA
        assert workspace.read_text(Path("src/service.py")) == "VALUE = 1\n"
        with pytest.raises(UnsafeWorkspacePath):
            workspace.read_text(Path("../secret"))

    assert not root.exists()
    assert tuple(command for command, _, _ in commands) == (
        ["git", "init", "--quiet"],
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/example/runtime.git",
        ],
        ["git", "fetch", "--quiet", "--depth=1", "origin", SHA],
        ["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"],
    )
    environment = commands[0][2]
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_CONFIG_VALUE_1"] != ""
    assert "installation-token" not in " ".join(commands[2][0])


def test_workspace_rejects_escaping_symlinks_and_oversized_files(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("outside\n", encoding="utf-8")

    def run(
        command: list[str],
        workspace: Path,
        environment: Mapping[str, str],
    ) -> None:
        if command[:2] == ["git", "checkout"]:
            (workspace / "escape.py").symlink_to(outside)
            (workspace / "large.py").write_text("x" * 20, encoding="utf-8")

    manager = WorkspaceManager(
        base_directory=tmp_path,
        max_file_bytes=10,
        command_runner=run,
    )

    with manager.prepare(
        clone_url="https://github.com/example/runtime.git",
        commit_sha=SHA,
        token="token",
    ) as workspace:
        with pytest.raises(UnsafeWorkspacePath, match="escapes"):
            workspace.read_text(Path("escape.py"))
        with pytest.raises(UnsafeWorkspacePath, match="size limit"):
            workspace.read_text(Path("large.py"))


def test_workspace_cleanup_occurs_when_preparation_or_execution_fails(
    tmp_path: Path,
) -> None:
    def fail(
        command: list[str],
        workspace: Path,
        environment: Mapping[str, str],
    ) -> None:
        raise RuntimeError("git failed")

    manager = WorkspaceManager(base_directory=tmp_path, command_runner=fail)

    with pytest.raises(WorkspacePreparationError):
        with manager.prepare(
            clone_url="https://github.com/example/runtime.git",
            commit_sha=SHA,
            token="token",
        ):
            pass

    assert tuple(tmp_path.iterdir()) == ()


def test_workspace_cleanup_occurs_when_execution_body_raises(tmp_path: Path) -> None:
    def run(
        command: list[str],
        workspace: Path,
        environment: Mapping[str, str],
    ) -> None:
        pass

    manager = WorkspaceManager(base_directory=tmp_path, command_runner=run)
    root: Path | None = None

    with pytest.raises(RuntimeError, match="execution failed"):
        with manager.prepare(
            clone_url="https://github.com/example/runtime.git",
            commit_sha=SHA,
            token="token",
        ) as workspace:
            root = workspace.root
            raise RuntimeError("execution failed")

    assert root is not None
    assert not root.exists()


@pytest.mark.parametrize(
    ("clone_url", "commit_sha"),
    [
        ("file:///tmp/repository", SHA),
        ("https://attacker.example/runtime.git", SHA),
        ("https://token@github.com/example/runtime.git", SHA),
        ("https://github.com/example/runtime.git", "branch-name"),
    ],
)
def test_workspace_requires_https_and_an_exact_full_sha(
    tmp_path: Path,
    clone_url: str,
    commit_sha: str,
) -> None:
    manager = WorkspaceManager(base_directory=tmp_path)

    with pytest.raises(WorkspacePreparationError):
        with manager.prepare(
            clone_url=clone_url,
            commit_sha=commit_sha,
            token="token",
        ):
            pass

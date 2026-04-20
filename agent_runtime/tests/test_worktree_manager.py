"""Tests for linked worktree allocation and release."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.orchestrator.worktree_manager import (
    allocate_worktree,
    bind_worktree_to_execution,
    release_worktree,
)
from agent_runtime.runners.contracts import RunnerExecution, RunnerName
from agent_runtime.storage.sqlite import load_active_worktree_lease, load_worktree_lease


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def test_allocate_reuse_and_release_worktree() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        repo_root = temp_path / "repo"
        repo_root.mkdir()

        _git(repo_root, "init")
        _git(repo_root, "config", "user.email", "test@example.com")
        _git(repo_root, "config", "user.name", "Test User")
        (repo_root / "README.md").write_text("runtime test\n", encoding="utf-8")
        _git(repo_root, "add", "README.md")
        _git(repo_root, "commit", "-m", "init")

        defaults = RuntimeDefaults(repo_root=repo_root, worktree_root_dirname="repo-worktrees")
        db_path = repo_root / ".agent_runtime" / "state.db"
        execution = RunnerExecution(
            runner_name=RunnerName.PM,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the PM agent.",
            metadata={"base_ref": "HEAD"},
        )

        lease = allocate_worktree(defaults, db_path, execution)
        active = load_active_worktree_lease(db_path, execution.work_item_id, execution.runner_name.value)

        assert active is not None
        assert active.run_id == lease.run_id
        assert active.branch_name == lease.branch_name
        assert Path(lease.worktree_path).is_dir()

        bound_execution = bind_worktree_to_execution(execution, lease)
        assert bound_execution.prompt.startswith("Execution checkout (agent_runtime authoritative):")
        assert lease.run_id in bound_execution.prompt
        assert bound_execution.metadata["run_id"] == lease.run_id
        assert bound_execution.metadata["execution_mode"] == "runtime_managed"
        assert bound_execution.metadata["worktree_path"] == lease.worktree_path

        reused = allocate_worktree(defaults, db_path, execution)
        assert reused.run_id == lease.run_id

        release_status = release_worktree(defaults, db_path, lease.run_id)
        released = load_worktree_lease(db_path, lease.run_id)

        assert release_status == "released"
        assert released is not None
        assert released.status == "released"
        assert released.released_at is not None
        assert not Path(lease.worktree_path).exists()


def test_release_worktree_reports_missing_or_already_released() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        repo_root = temp_path / "repo"
        repo_root.mkdir()

        _git(repo_root, "init")
        _git(repo_root, "config", "user.email", "test@example.com")
        _git(repo_root, "config", "user.name", "Test User")
        (repo_root / "README.md").write_text("runtime test\n", encoding="utf-8")
        _git(repo_root, "add", "README.md")
        _git(repo_root, "commit", "-m", "init")

        defaults = RuntimeDefaults(repo_root=repo_root, worktree_root_dirname="repo-worktrees")
        db_path = repo_root / ".agent_runtime" / "state.db"
        execution = RunnerExecution(
            runner_name=RunnerName.PM,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the PM agent.",
            metadata={"base_ref": "HEAD"},
        )

        lease = allocate_worktree(defaults, db_path, execution)
        assert release_worktree(defaults, db_path, lease.run_id) == "released"
        assert release_worktree(defaults, db_path, lease.run_id) == "already_released"
        assert release_worktree(defaults, db_path, "missing-run") == "not_found"

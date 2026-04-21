"""Tests for linked worktree allocation and release."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import sqlite3

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.orchestrator.worktree_manager import (
    allocate_worktree,
    bind_worktree_to_execution,
    release_worktree,
)
from agent_runtime.runners.contracts import RunnerExecution, RunnerName
from agent_runtime.storage.sqlite import (
    WorktreeLeaseRecord,
    insert_worktree_lease,
    load_active_worktree_lease,
    load_worktree_lease,
)


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


def test_allocate_worktree_replaces_stale_gitdir_stub() -> None:
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

        stale_worktree = temp_path / "stale-worktree"
        stale_worktree.mkdir()
        (stale_worktree / ".git").write_text("gitdir: /tmp/missing-runtime-gitdir\n", encoding="utf-8")
        stale_run_id = "pm-wi-1-1-4-risk-summary-core-service-stale"
        insert_worktree_lease(
            db_path,
            WorktreeLeaseRecord(
                run_id=stale_run_id,
                work_item_id=execution.work_item_id,
                runner_name=execution.runner_name.value,
                branch_name="codex/pm-wi-1-1-4-stale",
                base_ref="HEAD",
                worktree_path=str(stale_worktree),
                status="active",
            ),
        )

        lease = allocate_worktree(defaults, db_path, execution)
        stale = load_worktree_lease(db_path, stale_run_id)

        assert lease.run_id != stale_run_id
        assert stale is not None
        assert stale.status == "released"

        rev_parse = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=lease.worktree_path,
            check=True,
            capture_output=True,
            text=True,
        )
        assert rev_parse.stdout.strip() == "true"


def test_release_worktree_keeps_non_runtime_owned_branch() -> None:
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
        _git(repo_root, "branch", "pr/head")

        defaults = RuntimeDefaults(repo_root=repo_root, worktree_root_dirname="repo-worktrees")
        db_path = repo_root / ".agent_runtime" / "state.db"
        execution = RunnerExecution(
            runner_name=RunnerName.REVIEW,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the review agent.",
            metadata={
                "base_ref": "HEAD",
                "checkout_ref": "HEAD",
                "checkout_detached": "true",
                "branch_owned_by_runtime": "false",
                "pr_head_branch": "pr/head",
            },
        )

        lease = allocate_worktree(defaults, db_path, execution)
        assert lease.branch_name == "pr/head"
        assert lease.branch_owned_by_runtime is False

        assert release_worktree(defaults, db_path, lease.run_id) == "released"

        branch_check = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/pr/head"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        assert branch_check.returncode == 0


def test_allocate_worktree_replaces_stale_detached_checkout_when_target_ref_advances() -> None:
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
        _git(repo_root, "branch", "pr/head")

        defaults = RuntimeDefaults(repo_root=repo_root, worktree_root_dirname="repo-worktrees")
        db_path = repo_root / ".agent_runtime" / "state.db"
        execution = RunnerExecution(
            runner_name=RunnerName.REVIEW,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the review agent.",
            metadata={
                "base_ref": "HEAD",
                "checkout_ref": "pr/head",
                "checkout_detached": "true",
                "branch_owned_by_runtime": "false",
                "pr_head_branch": "pr/head",
            },
        )

        initial_lease = allocate_worktree(defaults, db_path, execution)
        initial_worktree_path = Path(initial_lease.worktree_path)

        initial_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=initial_worktree_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        (repo_root / "README.md").write_text("runtime test advanced\n", encoding="utf-8")
        _git(repo_root, "add", "README.md")
        _git(repo_root, "commit", "-m", "advance pr head")
        _git(repo_root, "branch", "-f", "pr/head", "HEAD")

        updated_target = subprocess.run(
            ["git", "rev-parse", "pr/head"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert updated_target != initial_head

        refreshed_lease = allocate_worktree(defaults, db_path, execution)
        released_initial = load_worktree_lease(db_path, initial_lease.run_id)

        assert refreshed_lease.run_id != initial_lease.run_id
        assert released_initial is not None
        assert released_initial.status == "released"
        assert not initial_worktree_path.exists()

        refreshed_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=refreshed_lease.worktree_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert refreshed_head == updated_target


def test_allocate_worktree_cleans_orphaned_worktree_when_lease_insert_loses_race() -> None:
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
        concurrent_lease = WorktreeLeaseRecord(
            run_id="pm-wi-1-1-4-concurrent",
            work_item_id=execution.work_item_id,
            runner_name=execution.runner_name.value,
            branch_name="codex/pm-wi-1-1-4-concurrent",
            base_ref="HEAD",
            worktree_path=str(temp_path / "other-worktree"),
            status="active",
        )
        load_calls = 0

        def fake_load_active(*args: object, **kwargs: object) -> WorktreeLeaseRecord | None:
            del args, kwargs
            nonlocal load_calls
            load_calls += 1
            if load_calls == 1:
                return None
            return concurrent_lease

        with patch("agent_runtime.orchestrator.worktree_manager.load_active_worktree_lease", side_effect=fake_load_active):
            with patch(
                "agent_runtime.orchestrator.worktree_manager.insert_worktree_lease",
                side_effect=sqlite3.IntegrityError("active runner lease already exists"),
            ):
                reused_lease = allocate_worktree(defaults, db_path, execution)

        assert reused_lease == concurrent_lease
        assert not defaults.worktree_root_path.exists() or tuple(defaults.worktree_root_path.iterdir()) == ()

        branch_listing = subprocess.run(
            ["git", "branch", "--list", "codex/*"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        assert branch_listing.stdout.strip() == ""

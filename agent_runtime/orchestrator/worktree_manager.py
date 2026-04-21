"""Allocate isolated git worktrees for repository agent runs."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import re
import subprocess
import uuid
import sqlite3

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.runners.contracts import RunnerExecution
from agent_runtime.storage.sqlite import (
    WorktreeLeaseRecord,
    insert_worktree_lease,
    load_active_worktree_lease,
    load_worktree_lease,
    mark_worktree_lease_released,
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or "run"


def _git(repo_root: Path, *args: str) -> None:
    try:
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip()
        detail = f"\n{stderr}" if stderr else ""
        raise RuntimeError(f"git command failed: {' '.join(error.cmd)}{detail}") from error


def _build_run_id(execution: RunnerExecution) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    token = uuid.uuid4().hex[:8]
    return f"{execution.runner_name.value}-{_slugify(execution.work_item_id)}-{timestamp}-{token}"


def _build_branch_name(execution: RunnerExecution, run_id: str) -> str:
    branch_slug = _slugify(f"{execution.runner_name.value}-{execution.work_item_id}")
    return f"codex/{branch_slug}-{run_id.split('-')[-1]}"


def _inject_runtime_checkout_context(prompt: str, lease: WorktreeLeaseRecord, metadata: dict[str, str]) -> str:
    context_block = (
        "Execution checkout (agent_runtime authoritative):\n"
        f"- run_id: {lease.run_id}\n"
        f"- worktree_path: {lease.worktree_path}\n"
        f"- branch_name: {lease.branch_name}\n"
        f"- base_ref: {lease.base_ref}\n"
    )
    if metadata.get("checkout_detached") == "true" and metadata.get("checkout_ref"):
        context_block += f"- checkout_ref: {metadata['checkout_ref']}\n"
    if metadata.get("pr_head_branch"):
        context_block += f"- pr_head_branch: {metadata['pr_head_branch']}\n"
    context_block += (
        "\n"
        "Checkout rule:\n"
        "- do all work only in this worktree\n"
        "- do not switch to `main`\n"
        "- do not create another worktree\n"
        "- do not create another branch\n"
    )
    if metadata.get("checkout_detached") == "true" and metadata.get("pr_head_branch"):
        context_block += f"- when pushing follow-up commits, use `git push origin HEAD:{metadata['pr_head_branch']}`\n"
    if context_block in prompt:
        return prompt
    return f"{context_block}\n{prompt}"


def _best_effort_git(repo_root: Path, *args: str) -> RuntimeError | None:
    try:
        _git(repo_root, *args)
    except RuntimeError as error:
        return error
    return None


def _is_valid_worktree(path: Path) -> bool:
    if not path.exists() or not (path / ".git").exists():
        return False

    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=path,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _cleanup_stale_lease(defaults: RuntimeDefaults, db_path: Path, lease: WorktreeLeaseRecord) -> None:
    _best_effort_git(defaults.repo_root, "worktree", "prune")
    if lease.branch_owned_by_runtime:
        _best_effort_git(defaults.repo_root, "branch", "-D", lease.branch_name)
    mark_worktree_lease_released(db_path, lease.run_id)


def _checkout_plan(execution: RunnerExecution, run_id: str) -> tuple[str, str, bool, bool]:
    base_ref = execution.metadata.get("base_ref", "origin/main")
    checkout_ref = execution.metadata.get("checkout_ref", base_ref)
    checkout_detached = execution.metadata.get("checkout_detached") == "true"
    branch_owned_by_runtime = execution.metadata.get("branch_owned_by_runtime", "true") != "false"
    branch_name = execution.metadata.get("pr_head_branch") or _build_branch_name(execution, run_id)
    return branch_name, checkout_ref, checkout_detached, branch_owned_by_runtime


def allocate_worktree(
    defaults: RuntimeDefaults,
    db_path: Path,
    execution: RunnerExecution,
) -> WorktreeLeaseRecord:
    existing = load_active_worktree_lease(db_path, execution.work_item_id, execution.runner_name.value)
    if existing is not None:
        worktree_path = Path(existing.worktree_path)
        if _is_valid_worktree(worktree_path):
            return existing
        _cleanup_stale_lease(defaults, db_path, existing)

    run_id = _build_run_id(execution)
    base_ref = execution.metadata.get("base_ref", "origin/main")
    branch_name, checkout_ref, checkout_detached, branch_owned_by_runtime = _checkout_plan(execution, run_id)
    worktree_dirname = _slugify(f"{execution.runner_name.value}-{execution.work_item_id}-{run_id.split('-')[-1]}")
    worktree_path = defaults.worktree_root_path / worktree_dirname

    defaults.worktree_root_path.mkdir(parents=True, exist_ok=True)
    if checkout_ref.startswith("origin/") or base_ref.startswith("origin/"):
        _git(defaults.repo_root, "fetch", "origin")
    if checkout_detached:
        _git(defaults.repo_root, "worktree", "add", "--detach", str(worktree_path), checkout_ref)
    else:
        _git(defaults.repo_root, "worktree", "add", "-b", branch_name, str(worktree_path), checkout_ref)

    lease = WorktreeLeaseRecord(
        run_id=run_id,
        work_item_id=execution.work_item_id,
        runner_name=execution.runner_name.value,
        branch_name=branch_name,
        base_ref=base_ref,
        worktree_path=str(worktree_path),
        status="active",
        branch_owned_by_runtime=branch_owned_by_runtime,
    )
    try:
        insert_worktree_lease(db_path, lease)
    except sqlite3.IntegrityError:
        concurrent_lease = load_active_worktree_lease(db_path, execution.work_item_id, execution.runner_name.value)
        if concurrent_lease is None:
            raise
        return concurrent_lease
    return lease


def bind_worktree_to_execution(execution: RunnerExecution, lease: WorktreeLeaseRecord) -> RunnerExecution:
    metadata = {
        **dict(execution.metadata),
        "execution_mode": "runtime_managed",
        "run_id": lease.run_id,
        "worktree_path": lease.worktree_path,
        "branch_name": lease.branch_name,
        "base_ref": lease.base_ref,
        "branch_owned_by_runtime": "true" if lease.branch_owned_by_runtime else "false",
    }
    return replace(execution, prompt=_inject_runtime_checkout_context(execution.prompt, lease, metadata), metadata=metadata)


def release_worktree(defaults: RuntimeDefaults, db_path: Path, run_id: str) -> str:
    lease = load_worktree_lease(db_path, run_id)
    if lease is None:
        return "not_found"
    if lease.status != "active":
        return "already_released"

    cleanup_error: RuntimeError | None = None
    try:
        error = _best_effort_git(defaults.repo_root, "worktree", "remove", "--force", lease.worktree_path)
        if error is not None:
            cleanup_error = error

        if lease.branch_owned_by_runtime:
            error = _best_effort_git(defaults.repo_root, "branch", "-D", lease.branch_name)
            if cleanup_error is None and error is not None:
                cleanup_error = error
    finally:
        mark_worktree_lease_released(db_path, run_id)

    if cleanup_error is not None:
        raise cleanup_error
    return "released"

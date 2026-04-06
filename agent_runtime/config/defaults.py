"""Default runtime configuration values."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeDefaults:
    repo_root: Path
    poll_interval_seconds: int = 600
    state_db_relative_path: str = ".agent_runtime/state.db"
    supervisor_lock_relative_path: str = ".agent_runtime/supervisor.lock"
    worktree_root_dirname: str | None = None
    ready_work_items_relative_path: str = "work_items/ready"
    in_progress_work_items_relative_path: str = "work_items/in_progress"
    blocked_work_items_relative_path: str = "work_items/blocked"
    # Iter 1: autonomous execution
    runner_timeout_seconds_coding: int = 2700  # 45 min
    runner_timeout_seconds_default: int = 900  # 15 min
    runner_max_retries: int = 2
    # Iter 3: parallel dispatch
    max_concurrent_runs: int = 3

    @property
    def state_db_path(self) -> Path:
        return self.repo_root / self.state_db_relative_path

    @property
    def supervisor_lock_path(self) -> Path:
        return self.repo_root / self.supervisor_lock_relative_path

    @property
    def worktree_root_path(self) -> Path:
        dirname = self.worktree_root_dirname or f"{self.repo_root.name}-worktrees"
        return self.repo_root.parent / dirname


def build_defaults(repo_root: Path) -> RuntimeDefaults:
    return RuntimeDefaults(repo_root=repo_root)

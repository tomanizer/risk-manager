"""Default runtime configuration values."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeDefaults:
    repo_root: Path
    poll_interval_seconds: int = 600
    state_db_relative_path: str = ".agent_runtime/state.db"
    ready_work_items_relative_path: str = "work_items/ready"
    in_progress_work_items_relative_path: str = "work_items/in_progress"
    blocked_work_items_relative_path: str = "work_items/blocked"

    @property
    def state_db_path(self) -> Path:
        return self.repo_root / self.state_db_relative_path


def build_defaults(repo_root: Path) -> RuntimeDefaults:
    return RuntimeDefaults(repo_root=repo_root)

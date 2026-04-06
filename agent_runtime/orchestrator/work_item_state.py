"""Work item stage mutations for the agent runtime.

Provides helpers to move work item markdown files between the folder-based
stage directories (``ready/``, ``in_progress/``, ``blocked/``, ``done/``).

These mutations are called by the orchestrator after a completed runner
outcome so that the folder-based work item registry stays coherent with
the SQLite state — removing the need for a human to manually move files.

The expected folder layout mirrors the registry loader:

    work_items/
        ready/        ← ready for the next PM/Coding/Review cycle
        in_progress/  ← actively being worked by an agent
        blocked/      ← waiting on external input or human decision
        done/         ← merged, closed, or explicitly completed
        archived/     ← long-term archive
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from agent_runtime.config.defaults import RuntimeDefaults

_log = logging.getLogger(__name__)


def _resolve_stage_dir(defaults: RuntimeDefaults, relative: str) -> Path:
    return defaults.repo_root / relative


def move_work_item(
    work_item_path: Path,
    target_dir: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Move a work item file to ``target_dir``.

    Returns the new path.  Raises ``FileNotFoundError`` if the source does
    not exist.  Raises ``FileExistsError`` if the target already exists and
    ``overwrite`` is ``False``.
    """
    if not work_item_path.is_file():
        raise FileNotFoundError(f"Work item not found: {work_item_path}")

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / work_item_path.name

    if target_path.exists() and not overwrite:
        raise FileExistsError(f"Target already exists: {target_path}")

    shutil.move(str(work_item_path), target_path)
    _log.info("Moved work item %s → %s", work_item_path.name, target_path)
    return target_path


def move_to_in_progress(work_item_path: Path, defaults: RuntimeDefaults) -> Path:
    """Move a work item from ``ready/`` to ``in_progress/`` after PM outcome 'ready'."""
    target_dir = _resolve_stage_dir(defaults, defaults.in_progress_work_items_relative_path)
    return move_work_item(work_item_path, target_dir)


def move_to_blocked(work_item_path: Path, defaults: RuntimeDefaults) -> Path:
    """Move a work item to ``blocked/`` after PM/Spec/Coding outcome 'blocked'."""
    target_dir = _resolve_stage_dir(defaults, defaults.blocked_work_items_relative_path)
    return move_work_item(work_item_path, target_dir)


def move_to_done(work_item_path: Path, defaults: RuntimeDefaults) -> Path:
    """Move a work item from ``in_progress/`` to ``done/`` after a merged PR."""
    done_dir = defaults.repo_root / "work_items" / "done"
    return move_work_item(work_item_path, done_dir)


def maybe_advance_work_item_stage(
    defaults: RuntimeDefaults,
    work_item_path: Path | None,
    outcome_status: str | None,
    action: str | None,
) -> str | None:
    """Advance the work item stage file based on the completed outcome.

    Returns the new path as a string, or ``None`` if no move was warranted.

    This is a best-effort operation: errors are logged but do not propagate,
    since the SQLite record is the authoritative state.
    """
    if work_item_path is None or not work_item_path.is_file():
        return None

    try:
        if action in {"run_pm"} and outcome_status == "ready":
            new_path = move_to_in_progress(work_item_path, defaults)
            return str(new_path)
        if outcome_status == "blocked":
            new_path = move_to_blocked(work_item_path, defaults)
            return str(new_path)
        if action in {"human_merge"} or outcome_status == "merged":
            new_path = move_to_done(work_item_path, defaults)
            return str(new_path)
    except (FileNotFoundError, FileExistsError, OSError) as exc:
        _log.warning("Could not advance work item stage for %s: %s", work_item_path, exc)

    return None

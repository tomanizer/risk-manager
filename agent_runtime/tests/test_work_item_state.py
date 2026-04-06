"""Tests for work item stage mutations (Iter 5)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.orchestrator.work_item_state import (
    maybe_advance_work_item_stage,
    move_to_blocked,
    move_to_done,
    move_to_in_progress,
)


def _make_defaults(tmp_dir: str) -> RuntimeDefaults:
    root = Path(tmp_dir)
    (root / "work_items" / "ready").mkdir(parents=True)
    return RuntimeDefaults(repo_root=root)


def _make_work_item(directory: Path, name: str = "WI-1.md") -> Path:
    path = directory / name
    path.write_text("# WI-1\n", encoding="utf-8")
    return path


class TestMoveToInProgress:
    def test_moves_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            ready_dir = Path(tmp) / "work_items" / "ready"
            wi = _make_work_item(ready_dir)

            new_path = move_to_in_progress(wi, defaults)

            assert not wi.exists()
            assert new_path.exists()
            assert "in_progress" in str(new_path)

    def test_raises_if_source_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            missing = Path(tmp) / "work_items" / "ready" / "no-such.md"
            with pytest.raises(FileNotFoundError):
                move_to_in_progress(missing, defaults)


class TestMoveToBlocked:
    def test_moves_to_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            ready_dir = Path(tmp) / "work_items" / "ready"
            wi = _make_work_item(ready_dir)

            new_path = move_to_blocked(wi, defaults)
            assert "blocked" in str(new_path)
            assert new_path.exists()


class TestMoveToDone:
    def test_moves_to_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            ready_dir = Path(tmp) / "work_items" / "ready"
            wi = _make_work_item(ready_dir)

            new_path = move_to_done(wi, defaults)
            assert "done" in str(new_path)
            assert new_path.exists()


class TestMaybeAdvanceWorkItemStage:
    def test_pm_ready_moves_to_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            ready_dir = Path(tmp) / "work_items" / "ready"
            wi = _make_work_item(ready_dir)

            result = maybe_advance_work_item_stage(defaults, wi, "ready", "run_pm")
            assert result is not None
            assert "in_progress" in result

    def test_blocked_outcome_moves_to_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            ready_dir = Path(tmp) / "work_items" / "ready"
            wi = _make_work_item(ready_dir)

            result = maybe_advance_work_item_stage(defaults, wi, "blocked", "run_pm")
            assert result is not None
            assert "blocked" in result

    def test_none_path_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            result = maybe_advance_work_item_stage(defaults, None, "ready", "run_pm")
            assert result is None

    def test_nonexistent_path_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            nonexistent = Path(tmp) / "nonexistent.md"
            result = maybe_advance_work_item_stage(defaults, nonexistent, "ready", "run_pm")
            assert result is None

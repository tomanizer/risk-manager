"""Tests for the parallel dispatch engine (Iter 3)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import cast
from unittest.mock import patch


from alterraflow.config.defaults import RuntimeDefaults
from alterraflow.orchestrator.parallel_dispatch import (
    _has_active_lease,
    _pick_primary_result,
    run_parallel_step,
)
from alterraflow.orchestrator.state import (
    NextActionType,
    RuntimeSnapshot,
    TransitionDecision,
    WorkItemSnapshot,
)
from alterraflow.runners.contracts import RunnerExecution, RunnerName


def _make_defaults(tmp_dir: str) -> RuntimeDefaults:
    return RuntimeDefaults(repo_root=Path(tmp_dir), max_concurrent_runs=2)


def _make_snapshot(work_items: tuple[WorkItemSnapshot, ...] = ()) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        work_items=work_items,
        pull_requests=(),
        workflow_runs=(),
        warnings=(),
    )


class TestPickPrimaryResult:
    def test_empty_returns_noop(self) -> None:
        result = _pick_primary_result([])
        assert result["action"] == NextActionType.NOOP.value

    def test_failed_takes_priority_over_completed(self) -> None:
        results = cast(
            list[dict[str, object]],
            [
                {"action": "run_pm", "runner_result": {"status": "completed"}},
                {"action": "run_coding", "runner_result": {"status": "failed"}},
            ],
        )
        primary = _pick_primary_result(results)
        rr = primary.get("runner_result")
        assert isinstance(rr, dict) and rr["status"] == "failed"

    def test_timed_out_priority_over_completed(self) -> None:
        results = cast(
            list[dict[str, object]],
            [
                {"action": "run_pm", "runner_result": {"status": "completed"}},
                {"action": "run_coding", "runner_result": {"status": "timed_out"}},
            ],
        )
        primary = _pick_primary_result(results)
        rr = primary.get("runner_result")
        assert isinstance(rr, dict) and rr["status"] == "timed_out"

    def test_single_result_returned(self) -> None:
        results = cast(
            list[dict[str, object]],
            [
                {"action": "run_pm", "runner_result": {"status": "completed"}},
            ],
        )
        primary = _pick_primary_result(results)
        rr = primary.get("runner_result")
        assert isinstance(rr, dict) and rr["status"] == "completed"


class TestHasActiveLease:
    def test_returns_false_when_no_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            snapshot = _make_snapshot()
            decision = TransitionDecision(
                action=NextActionType.RUN_PM,
                work_item_id="WI-1",
                reason="test",
            )
            assert _has_active_lease(defaults, snapshot, decision) is False

    def test_returns_false_for_none_work_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            snapshot = _make_snapshot()
            decision = TransitionDecision(
                action=NextActionType.NOOP,
                work_item_id=None,
                reason="test",
            )
            assert _has_active_lease(defaults, snapshot, decision) is False

    def test_returns_false_when_active_lease_is_not_reusable_for_current_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            snapshot = _make_snapshot()
            decision = TransitionDecision(
                action=NextActionType.RUN_PM,
                work_item_id="WI-1",
                reason="test",
            )
            execution = RunnerExecution(
                runner_name=RunnerName.PM,
                work_item_id="WI-1",
                prompt="test prompt",
                metadata={"base_ref": "origin/main"},
            )

            with patch("alterraflow.orchestrator.parallel_dispatch.build_runner_execution", return_value=execution):
                with patch("alterraflow.orchestrator.parallel_dispatch.has_reusable_active_worktree_lease", return_value=False):
                    assert _has_active_lease(defaults, snapshot, decision) is False


class TestRunParallelStep:
    def test_returns_noop_when_no_work_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            snapshot = _make_snapshot()
            result = run_parallel_step(defaults, snapshot)
            assert result["action"] == NextActionType.NOOP.value
            assert result["parallel_results"] == []

    def test_respects_concurrency_budget(self) -> None:
        """All decisions are dispatched up to max_concurrent_runs budget."""
        with tempfile.TemporaryDirectory() as tmp:
            defaults = RuntimeDefaults(repo_root=Path(tmp), max_concurrent_runs=1)
            # We mock decide_all_actions to return 3 dispatchable decisions
            decisions = tuple(
                TransitionDecision(
                    action=NextActionType.RUN_PM,
                    work_item_id=f"WI-{i}",
                    reason="test",
                )
                for i in range(3)
            )
            dispatched: list[str] = []

            def _mock_dispatch(defaults: RuntimeDefaults, snapshot: RuntimeSnapshot, decision: TransitionDecision) -> dict[str, object]:
                dispatched.append(str(decision.work_item_id))
                return {
                    "action": decision.action.value,
                    "work_item_id": decision.work_item_id,
                    "reason": decision.reason,
                    "retry_count": 0,
                    "runner_result": {"status": "completed"},
                }

            snapshot = _make_snapshot()
            with patch("alterraflow.orchestrator.parallel_dispatch.decide_all_actions", return_value=decisions):
                with patch("alterraflow.orchestrator.parallel_dispatch._dispatch_one", side_effect=_mock_dispatch):
                    result = run_parallel_step(defaults, snapshot)

            assert len(dispatched) == 1  # budget = 1
            assert result["parallel_results"] is not None

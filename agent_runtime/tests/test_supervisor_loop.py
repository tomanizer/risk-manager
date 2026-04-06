"""Tests for the supervised runtime loop helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path

from agent_runtime.orchestrator.supervisor import LoopControl, classify_loop_payload
from agent_runtime.storage.sqlite import SupervisorStateRecord, load_supervisor_state, upsert_supervisor_state


def test_classify_loop_payload_waits_for_reviews() -> None:
    payload = {
        "action": "wait_for_reviews",
        "runner_result": None,
    }

    control = classify_loop_payload(payload, 300)

    assert control == LoopControl(continue_polling=True, sleep_seconds=300, exit_code=0)


def test_classify_loop_payload_stops_on_prepared_runner() -> None:
    payload = {
        "action": "run_pm",
        "runner_result": {
            "status": "prepared",
        },
    }

    control = classify_loop_payload(payload, 300)

    assert control == LoopControl(continue_polling=False, sleep_seconds=None, exit_code=0)


def test_classify_loop_payload_continues_after_completed_runner() -> None:
    payload = {
        "action": "run_review",
        "runner_result": {
            "status": "completed",
        },
    }

    control = classify_loop_payload(payload, 300)

    assert control == LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)


def test_classify_loop_payload_stops_with_failure() -> None:
    payload = {
        "action": "run_coding",
        "runner_result": {
            "status": "failed",
        },
    }

    control = classify_loop_payload(payload, 300)

    assert control == LoopControl(continue_polling=False, sleep_seconds=None, exit_code=1)


def test_supervisor_state_round_trips() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        record = SupervisorStateRecord(
            status="waiting",
            lock_owner="lock-owner",
            mode="poll",
            heartbeat_at="2026-04-06 10:00:00",
            last_started_at="2026-04-06 09:59:00",
            last_completed_at="2026-04-06 10:00:00",
            last_action="wait_for_reviews",
            last_reason="PR checks are still running",
            active_run_id="review-run-1",
        )

        upsert_supervisor_state(db_path, record)
        loaded = load_supervisor_state(db_path)

        assert loaded is not None
        assert loaded.status == "waiting"
        assert loaded.lock_owner == "lock-owner"
        assert loaded.mode == "poll"
        assert loaded.heartbeat_at == "2026-04-06 10:00:00"
        assert loaded.last_action == "wait_for_reviews"
        assert loaded.active_run_id == "review-run-1"
        assert loaded.updated_at is not None

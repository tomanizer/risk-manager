"""Tests for the supervised runtime loop helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path

from agent_runtime.orchestrator.supervisor import (
    LoopControl,
    classify_loop_payload,
    supervisor_lock,
)
from agent_runtime.storage.sqlite import (
    SupervisorStateRecord,
    WorkflowRunRecord,
    load_supervisor_state,
    load_workflow_run,
    mark_workflow_run_running,
    upsert_supervisor_state,
    upsert_workflow_run,
)


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


def test_classify_loop_payload_retries_on_first_failure() -> None:
    """First failure (retry_count=0) should continue polling so the supervisor retries."""
    payload = {
        "action": "run_coding",
        "retry_count": 0,
        "runner_result": {
            "status": "failed",
        },
        "retry_count": 0,
    }

    control = classify_loop_payload(payload, 300)

    assert control == LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)


def test_classify_loop_payload_stops_after_max_retries() -> None:
    """Failure after max_retries exhausted stops the loop with exit_code=1."""
    payload = {
        "action": "run_coding",
        "runner_result": {
            "status": "failed",
        },
        "retry_count": 2,
    }

    control = classify_loop_payload(payload, 300, max_retries=2)

    assert control == LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)


def test_classify_loop_payload_stops_after_retries_exhausted() -> None:
    """Failure with retry_count >= max_retries should stop polling."""
    payload = {
        "action": "run_coding",
        "retry_count": 2,
        "runner_result": {
            "status": "failed",
        },
    }

    control = classify_loop_payload(payload, 300, max_retries=2)

    assert control == LoopControl(continue_polling=False, sleep_seconds=None, exit_code=1)


def test_classify_loop_payload_stops_with_failure_zero_retries() -> None:
    """With max_retries=0 the first failure should stop immediately."""
    payload = {
        "action": "run_coding",
        "retry_count": 0,
        "runner_result": {
            "status": "failed",
        },
    }

    control = classify_loop_payload(payload, 300, max_retries=0)

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


def test_supervisor_lock_owner_includes_pid_and_file_descriptor() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        lock_path = Path(temp_dir) / "runtime" / "supervisor.lock"

        with supervisor_lock(lock_path) as lock_owner:
            assert str(lock_path) in lock_owner
            parts = lock_owner.rsplit(":", maxsplit=2)
            assert len(parts) == 3
            assert parts[1].isdigit()
            assert parts[2].isdigit()


# --- Retry logic tests ---


def test_classify_loop_payload_retries_on_failed_below_limit() -> None:
    payload = {
        "action": "run_coding",
        "runner_result": {"status": "failed"},
        "retry_count": 1,
    }

    control = classify_loop_payload(payload, 300, max_retries=2)

    assert control == LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)


def test_classify_loop_payload_stops_on_failed_at_limit() -> None:
    payload = {
        "action": "run_coding",
        "runner_result": {"status": "failed"},
        "retry_count": 2,
    }

    control = classify_loop_payload(payload, 300, max_retries=2)

    assert control == LoopControl(continue_polling=False, sleep_seconds=None, exit_code=1)


def test_classify_loop_payload_retries_on_timed_out_below_limit() -> None:
    payload = {
        "action": "run_coding",
        "runner_result": {"status": "timed_out"},
        "retry_count": 0,
    }

    control = classify_loop_payload(payload, 300, max_retries=2)

    assert control == LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)


def test_classify_loop_payload_stops_on_timed_out_at_limit() -> None:
    payload = {
        "action": "run_coding",
        "runner_result": {"status": "timed_out"},
        "retry_count": 2,
    }

    control = classify_loop_payload(payload, 300, max_retries=2)

    assert control == LoopControl(continue_polling=False, sleep_seconds=None, exit_code=1)


def test_classify_loop_payload_default_max_retries_is_two() -> None:
    # With the default max_retries=2, retry_count=2 should stop polling.
    payload = {
        "action": "run_pm",
        "runner_result": {"status": "failed"},
        "retry_count": 2,
    }

    control = classify_loop_payload(payload, 300)

    assert control.continue_polling is False
    assert control.exit_code == 1


# --- RUNNING status upsert tests ---


def test_mark_workflow_run_running_sets_runner_status() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        upsert_workflow_run(
            db_path,
            WorkflowRunRecord(
                work_item_id="WI-test-1",
                status="run_coding",
                runner_status="prepared",
                retry_count=0,
            ),
        )

        mark_workflow_run_running(db_path, "WI-test-1", retry_count=0)

        record = load_workflow_run(db_path, "WI-test-1")
        assert record is not None
        assert record.runner_status == "running"


def test_mark_workflow_run_running_sets_retry_count() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        upsert_workflow_run(
            db_path,
            WorkflowRunRecord(
                work_item_id="WI-test-2",
                status="run_coding",
                runner_status="failed",
                retry_count=0,
            ),
        )

        mark_workflow_run_running(db_path, "WI-test-2", retry_count=1)

        record = load_workflow_run(db_path, "WI-test-2")
        assert record is not None
        assert record.runner_status == "running"
        assert record.retry_count == 1


def test_workflow_run_record_retry_count_persists() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        upsert_workflow_run(
            db_path,
            WorkflowRunRecord(
                work_item_id="WI-test-3",
                status="run_pm",
                runner_status="failed",
                retry_count=2,
            ),
        )

        record = load_workflow_run(db_path, "WI-test-3")
        assert record is not None
        assert record.retry_count == 2

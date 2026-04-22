"""Supervisor loop helpers for the repository runtime."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
import os
import time
from pathlib import Path
from typing import Generator, Mapping

from alterraflow.config.defaults import RuntimeDefaults
from alterraflow.storage.sqlite import SupervisorStateRecord, upsert_supervisor_state


@dataclass(frozen=True)
class LoopControl:
    continue_polling: bool
    sleep_seconds: int | None = None
    exit_code: int = 0


def classify_loop_payload(
    payload: Mapping[str, object],
    poll_interval_seconds: int,
    max_retries: int = 2,
) -> LoopControl:
    action = str(payload.get("action") or "")
    runner_result = payload.get("runner_result")
    if action in {"human_merge", "human_update_repo"}:
        return LoopControl(continue_polling=False, exit_code=0)
    if action in {"wait_for_reviews", "noop"}:
        return LoopControl(continue_polling=True, sleep_seconds=poll_interval_seconds, exit_code=0)
    if not isinstance(runner_result, dict):
        return LoopControl(continue_polling=False, exit_code=0)

    status = str(runner_result.get("status") or "")
    raw_retry = payload.get("retry_count")
    retry_count = int(raw_retry) if isinstance(raw_retry, int) else 0

    if status == "completed":
        return LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)
    if status == "prepared":
        return LoopControl(continue_polling=False, exit_code=0)
    if status in {"failed", "timed_out"}:
        if retry_count < max_retries:
            return LoopControl(continue_polling=True, sleep_seconds=0, exit_code=0)
        return LoopControl(continue_polling=False, exit_code=1)
    return LoopControl(continue_polling=False, exit_code=0)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def record_supervisor_heartbeat(
    defaults: RuntimeDefaults,
    *,
    status: str,
    lock_owner: str,
    mode: str,
    payload: dict[str, object] | None = None,
    started_at: str | None = None,
) -> None:
    runner = payload.get("runner") if isinstance(payload, dict) else None
    runner_metadata = runner.get("metadata") if isinstance(runner, dict) else None
    active_run_id = runner_metadata.get("run_id") if isinstance(runner_metadata, dict) else None
    upsert_supervisor_state(
        defaults.state_db_path,
        SupervisorStateRecord(
            status=status,
            lock_owner=lock_owner,
            mode=mode,
            heartbeat_at=_utc_now(),
            last_started_at=started_at,
            last_completed_at=_utc_now() if status in {"idle", "waiting", "stopped"} else None,
            last_action=str(payload.get("action")) if isinstance(payload, dict) and payload.get("action") is not None else None,
            last_reason=str(payload.get("reason")) if isinstance(payload, dict) and payload.get("reason") is not None else None,
            active_run_id=str(active_run_id) if active_run_id is not None else None,
        ),
    )


@contextmanager
def supervisor_lock(lock_path: Path) -> Generator[str, None, None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"another supervisor loop is already active for {lock_path}") from error
        lock_owner = f"{lock_path}:{os.getpid()}:{lock_file.fileno()}"
        lock_file.write(lock_owner)
        lock_file.flush()
        try:
            yield lock_owner
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def sleep_for_poll_interval(seconds: int) -> None:
    if seconds > 0:
        time.sleep(seconds)

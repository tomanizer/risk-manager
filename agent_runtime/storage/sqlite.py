"""Minimal SQLite state store scaffold for the runtime."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast


SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id     TEXT,
    span_id      TEXT,
    event_type   TEXT NOT NULL,
    component    TEXT NOT NULL,
    run_id       TEXT,
    work_item_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    level        TEXT NOT NULL DEFAULT 'INFO',
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_run
    ON telemetry_events(run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_type
    ON telemetry_events(event_type, created_at);

CREATE TABLE IF NOT EXISTS workflow_runs (
    work_item_id TEXT PRIMARY KEY,
    run_id TEXT,
    branch_name TEXT,
    pr_number INTEGER,
    status TEXT NOT NULL,
    blocked_reason TEXT,
    last_action TEXT,
    runner_name TEXT,
    runner_status TEXT,
    outcome_status TEXT,
    outcome_summary TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    outcome_details_json TEXT NOT NULL DEFAULT '{}',
    completed_at TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS worktree_leases (
    run_id TEXT PRIMARY KEY,
    work_item_id TEXT NOT NULL,
    runner_name TEXT NOT NULL,
    branch_name TEXT NOT NULL,
    base_ref TEXT NOT NULL,
    worktree_path TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at TEXT
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_item_id TEXT NOT NULL,
    action TEXT NOT NULL,
    runner_name TEXT,
    status TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_worktree_leases_active_runner
ON worktree_leases(work_item_id, runner_name)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_workflow_events_work_item
ON workflow_events(work_item_id, created_at);

CREATE TABLE IF NOT EXISTS supervisor_state (
    singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
    status TEXT NOT NULL,
    lock_owner TEXT,
    mode TEXT,
    heartbeat_at TEXT,
    last_started_at TEXT,
    last_completed_at TEXT,
    last_action TEXT,
    last_reason TEXT,
    active_run_id TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

EXPECTED_WORKFLOW_RUN_COLUMNS = (
    "work_item_id",
    "run_id",
    "branch_name",
    "pr_number",
    "status",
    "blocked_reason",
    "last_action",
    "runner_name",
    "runner_status",
    "outcome_status",
    "outcome_summary",
    "details_json",
    "result_json",
    "outcome_details_json",
    "completed_at",
    "retry_count",
    "updated_at",
)

EXPECTED_WORKTREE_LEASE_COLUMNS = (
    "run_id",
    "work_item_id",
    "runner_name",
    "branch_name",
    "base_ref",
    "worktree_path",
    "status",
    "created_at",
    "released_at",
)

EXPECTED_WORKFLOW_EVENT_COLUMNS = (
    "id",
    "work_item_id",
    "action",
    "runner_name",
    "status",
    "details_json",
    "created_at",
)

EXPECTED_SUPERVISOR_STATE_COLUMNS = (
    "singleton_id",
    "status",
    "lock_owner",
    "mode",
    "heartbeat_at",
    "last_started_at",
    "last_completed_at",
    "last_action",
    "last_reason",
    "active_run_id",
    "updated_at",
)

_DEFAULT_COLUMN_DEFINITIONS = {
    "run_id": "TEXT",
    "last_action": "TEXT",
    "runner_name": "TEXT",
    "runner_status": "TEXT",
    "outcome_status": "TEXT",
    "outcome_summary": "TEXT",
    "details_json": "TEXT NOT NULL DEFAULT '{}'",
    "result_json": "TEXT NOT NULL DEFAULT '{}'",
    "outcome_details_json": "TEXT NOT NULL DEFAULT '{}'",
    "retry_count": "INTEGER NOT NULL DEFAULT 0",
    "completed_at": "TEXT",
    "retry_count": "INTEGER NOT NULL DEFAULT 0",
    "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
}


@dataclass(frozen=True)
class WorkflowRunRecord:
    work_item_id: str
    status: str
    run_id: str | None = None
    branch_name: str | None = None
    pr_number: int | None = None
    blocked_reason: str | None = None
    last_action: str | None = None
    runner_name: str | None = None
    runner_status: str | None = None
    outcome_status: str | None = None
    outcome_summary: str | None = None
    details: dict[str, str] | None = None
    result: dict[str, object] = field(default_factory=dict)
    outcome_details: dict[str, object] = field(default_factory=dict)
    retry_count: int = 0
    completed_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class WorktreeLeaseRecord:
    run_id: str
    work_item_id: str
    runner_name: str
    branch_name: str
    base_ref: str
    worktree_path: str
    status: str
    created_at: str | None = None
    released_at: str | None = None


@dataclass(frozen=True)
class SupervisorStateRecord:
    status: str
    lock_owner: str | None = None
    mode: str | None = None
    heartbeat_at: str | None = None
    last_started_at: str | None = None
    last_completed_at: str | None = None
    last_action: str | None = None
    last_reason: str | None = None
    active_run_id: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class WorkflowEventRecord:
    work_item_id: str
    action: str
    runner_name: str | None = None
    status: str | None = None
    details: dict[str, str] | None = None
    created_at: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class TelemetryEventRecord:
    event_type: str
    component: str
    trace_id: str | None = None
    span_id: str | None = None
    run_id: str | None = None
    work_item_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
    level: str = "INFO"
    created_at: str | None = None
    id: int | None = None


def _verify_workflow_events_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(workflow_events)").fetchall()
    if not rows:
        raise RuntimeError("database initialization failed: workflow_events table was not created")

    actual_columns = {row[1] for row in rows}
    missing_columns = [column for column in EXPECTED_WORKFLOW_EVENT_COLUMNS if column not in actual_columns]
    if missing_columns:
        raise RuntimeError("database initialization failed: workflow_events table is missing columns: " + ", ".join(missing_columns))


def _verify_workflow_runs_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
    if not rows:
        raise RuntimeError("database initialization failed: workflow_runs table was not created")

    actual_columns = {row[1] for row in rows}
    missing_columns = [column for column in EXPECTED_WORKFLOW_RUN_COLUMNS if column not in actual_columns]
    if missing_columns:
        raise RuntimeError("database initialization failed: workflow_runs table is missing columns: " + ", ".join(missing_columns))


def _verify_worktree_leases_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(worktree_leases)").fetchall()
    if not rows:
        raise RuntimeError("database initialization failed: worktree_leases table was not created")

    actual_columns = {row[1] for row in rows}
    missing_columns = [column for column in EXPECTED_WORKTREE_LEASE_COLUMNS if column not in actual_columns]
    if missing_columns:
        raise RuntimeError("database initialization failed: worktree_leases table is missing columns: " + ", ".join(missing_columns))


def _verify_supervisor_state_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(supervisor_state)").fetchall()
    if not rows:
        raise RuntimeError("database initialization failed: supervisor_state table was not created")

    actual_columns = {row[1] for row in rows}
    missing_columns = [column for column in EXPECTED_SUPERVISOR_STATE_COLUMNS if column not in actual_columns]
    if missing_columns:
        raise RuntimeError("database initialization failed: supervisor_state table is missing columns: " + ", ".join(missing_columns))


def _ensure_expected_columns(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
    actual_columns = {row[1] for row in rows}
    for column_name in EXPECTED_WORKFLOW_RUN_COLUMNS:
        if column_name in actual_columns:
            continue
        column_definition = _DEFAULT_COLUMN_DEFINITIONS.get(column_name)
        if column_definition is None:
            continue
        connection.execute(f"ALTER TABLE workflow_runs ADD COLUMN {column_name} {column_definition}")


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        _ensure_expected_columns(connection)
        _verify_workflow_runs_schema(connection)
        _verify_worktree_leases_schema(connection)
        _verify_workflow_events_schema(connection)
        _verify_supervisor_state_schema(connection)
        connection.commit()


def upsert_workflow_run(db_path: Path, record: WorkflowRunRecord) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO workflow_runs (
                work_item_id,
                run_id,
                branch_name,
                pr_number,
                status,
                blocked_reason,
                last_action,
                runner_name,
                runner_status,
                outcome_status,
                outcome_summary,
                details_json,
                result_json,
                outcome_details_json,
                retry_count,
                completed_at,
                retry_count,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(work_item_id) DO UPDATE SET
                run_id = excluded.run_id,
                branch_name = excluded.branch_name,
                pr_number = excluded.pr_number,
                status = excluded.status,
                blocked_reason = excluded.blocked_reason,
                last_action = excluded.last_action,
                runner_name = excluded.runner_name,
                runner_status = excluded.runner_status,
                outcome_status = excluded.outcome_status,
                outcome_summary = excluded.outcome_summary,
                details_json = excluded.details_json,
                result_json = excluded.result_json,
                outcome_details_json = excluded.outcome_details_json,
                retry_count = excluded.retry_count,
                completed_at = excluded.completed_at,
                retry_count = excluded.retry_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.work_item_id,
                record.run_id,
                record.branch_name,
                record.pr_number,
                record.status,
                record.blocked_reason,
                record.last_action,
                record.runner_name,
                record.runner_status,
                record.outcome_status,
                record.outcome_summary,
                json.dumps(record.details or {}, sort_keys=True),
                json.dumps(record.result, sort_keys=True),
                json.dumps(record.outcome_details, sort_keys=True),
                record.retry_count,
                record.completed_at,
                record.retry_count,
            ),
        )
        connection.commit()


def load_workflow_run(db_path: Path, work_item_id: str) -> WorkflowRunRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                work_item_id,
                run_id,
                branch_name,
                pr_number,
                status,
                blocked_reason,
                last_action,
                runner_name,
                runner_status,
                outcome_status,
                outcome_summary,
                details_json,
                result_json,
                outcome_details_json,
                retry_count,
                completed_at,
                retry_count,
                updated_at
            FROM workflow_runs
            WHERE work_item_id = ?
            """,
            (work_item_id,),
        ).fetchone()

    return _row_to_workflow_run(row)


def load_workflow_run_by_run_id(db_path: Path, run_id: str) -> WorkflowRunRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                work_item_id,
                run_id,
                branch_name,
                pr_number,
                status,
                blocked_reason,
                last_action,
                runner_name,
                runner_status,
                outcome_status,
                outcome_summary,
                details_json,
                result_json,
                outcome_details_json,
                retry_count,
                completed_at,
                retry_count,
                updated_at
            FROM workflow_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    return _row_to_workflow_run(row)


def load_workflow_runs(db_path: Path) -> tuple[WorkflowRunRecord, ...]:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                work_item_id,
                run_id,
                branch_name,
                pr_number,
                status,
                blocked_reason,
                last_action,
                runner_name,
                runner_status,
                outcome_status,
                outcome_summary,
                details_json,
                result_json,
                outcome_details_json,
                retry_count,
                completed_at,
                retry_count,
                updated_at
            FROM workflow_runs
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return tuple(cast(WorkflowRunRecord, _row_to_workflow_run(row)) for row in rows)


def record_workflow_outcome(
    db_path: Path,
    run_id: str,
    outcome_status: str,
    outcome_summary: str,
    outcome_details: dict[str, object] | None = None,
) -> WorkflowRunRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE workflow_runs
            SET
                runner_status = 'completed',
                outcome_status = ?,
                outcome_summary = ?,
                outcome_details_json = ?,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE run_id = ?
            """,
            (
                outcome_status,
                outcome_summary,
                json.dumps(outcome_details or {}, sort_keys=True),
                run_id,
            ),
        )
        connection.commit()

    return load_workflow_run_by_run_id(db_path, run_id)


def mark_workflow_run_running(db_path: Path, work_item_id: str, retry_count: int = 0) -> None:
    """Write runner_status='running' immediately before a blocking dispatch.

    This allows a restarted supervisor to detect orphaned in-flight runs by
    looking for rows where runner_status='running' and updated_at is stale.
    """
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE workflow_runs
            SET runner_status = 'running', retry_count = ?, updated_at = CURRENT_TIMESTAMP
            WHERE work_item_id = ?
            """,
            (retry_count, work_item_id),
        )
        connection.commit()


def insert_worktree_lease(db_path: Path, record: WorktreeLeaseRecord) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO worktree_leases (
                run_id,
                work_item_id,
                runner_name,
                branch_name,
                base_ref,
                worktree_path,
                status,
                created_at,
                released_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?)
            ON CONFLICT(run_id) DO UPDATE SET
                work_item_id = excluded.work_item_id,
                runner_name = excluded.runner_name,
                branch_name = excluded.branch_name,
                base_ref = excluded.base_ref,
                worktree_path = excluded.worktree_path,
                status = excluded.status,
                released_at = excluded.released_at
            """,
            (
                record.run_id,
                record.work_item_id,
                record.runner_name,
                record.branch_name,
                record.base_ref,
                record.worktree_path,
                record.status,
                record.created_at,
                record.released_at,
            ),
        )
        connection.commit()


def load_active_worktree_lease(db_path: Path, work_item_id: str, runner_name: str) -> WorktreeLeaseRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                run_id,
                work_item_id,
                runner_name,
                branch_name,
                base_ref,
                worktree_path,
                status,
                created_at,
                released_at
            FROM worktree_leases
            WHERE work_item_id = ? AND runner_name = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (work_item_id, runner_name),
        ).fetchone()

    return _row_to_worktree_lease(row)


def load_worktree_lease(db_path: Path, run_id: str) -> WorktreeLeaseRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                run_id,
                work_item_id,
                runner_name,
                branch_name,
                base_ref,
                worktree_path,
                status,
                created_at,
                released_at
            FROM worktree_leases
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    return _row_to_worktree_lease(row)


def mark_worktree_lease_released(db_path: Path, run_id: str) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE worktree_leases
            SET status = 'released', released_at = CURRENT_TIMESTAMP
            WHERE run_id = ?
            """,
            (run_id,),
        )
        connection.commit()


def upsert_supervisor_state(db_path: Path, record: SupervisorStateRecord) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO supervisor_state (
                singleton_id,
                status,
                lock_owner,
                mode,
                heartbeat_at,
                last_started_at,
                last_completed_at,
                last_action,
                last_reason,
                active_run_id,
                updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(singleton_id) DO UPDATE SET
                status = excluded.status,
                lock_owner = excluded.lock_owner,
                mode = excluded.mode,
                heartbeat_at = excluded.heartbeat_at,
                last_started_at = excluded.last_started_at,
                last_completed_at = excluded.last_completed_at,
                last_action = excluded.last_action,
                last_reason = excluded.last_reason,
                active_run_id = excluded.active_run_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.status,
                record.lock_owner,
                record.mode,
                record.heartbeat_at,
                record.last_started_at,
                record.last_completed_at,
                record.last_action,
                record.last_reason,
                record.active_run_id,
            ),
        )
        connection.commit()


def load_supervisor_state(db_path: Path) -> SupervisorStateRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                singleton_id,
                status,
                lock_owner,
                mode,
                heartbeat_at,
                last_started_at,
                last_completed_at,
                last_action,
                last_reason,
                active_run_id,
                updated_at
            FROM supervisor_state
            WHERE singleton_id = 1
            """
        ).fetchone()

    if row is None:
        return None
    return SupervisorStateRecord(
        status=str(row["status"]),
        lock_owner=str(row["lock_owner"]) if row["lock_owner"] is not None else None,
        mode=str(row["mode"]) if row["mode"] is not None else None,
        heartbeat_at=str(row["heartbeat_at"]) if row["heartbeat_at"] is not None else None,
        last_started_at=str(row["last_started_at"]) if row["last_started_at"] is not None else None,
        last_completed_at=str(row["last_completed_at"]) if row["last_completed_at"] is not None else None,
        last_action=str(row["last_action"]) if row["last_action"] is not None else None,
        last_reason=str(row["last_reason"]) if row["last_reason"] is not None else None,
        active_run_id=str(row["active_run_id"]) if row["active_run_id"] is not None else None,
        updated_at=str(row["updated_at"]) if row["updated_at"] is not None else None,
    )


def _row_to_worktree_lease(row: sqlite3.Row | None) -> WorktreeLeaseRecord | None:
    if row is None:
        return None

    return WorktreeLeaseRecord(
        run_id=str(row["run_id"]),
        work_item_id=str(row["work_item_id"]),
        runner_name=str(row["runner_name"]),
        branch_name=str(row["branch_name"]),
        base_ref=str(row["base_ref"]),
        worktree_path=str(row["worktree_path"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]) if row["created_at"] is not None else None,
        released_at=str(row["released_at"]) if row["released_at"] is not None else None,
    )


def _row_to_workflow_run(row: sqlite3.Row | None) -> WorkflowRunRecord | None:
    if row is None:
        return None

    details_payload: object = {}
    details_json = row["details_json"]
    if details_json:
        try:
            details_payload = json.loads(details_json)
        except json.JSONDecodeError:
            details_payload = {}

    result_payload: object = {}
    result_json = row["result_json"]
    if result_json:
        try:
            result_payload = json.loads(result_json)
        except json.JSONDecodeError:
            result_payload = {}

    outcome_details_payload: object = {}
    outcome_details_json = row["outcome_details_json"]
    if outcome_details_json:
        try:
            outcome_details_payload = json.loads(outcome_details_json)
        except json.JSONDecodeError:
            outcome_details_payload = {}

    details = details_payload if isinstance(details_payload, dict) else {}
    result = {str(key): value for key, value in result_payload.items()} if isinstance(result_payload, dict) else {}
    outcome_details = {str(key): value for key, value in outcome_details_payload.items()} if isinstance(outcome_details_payload, dict) else {}
    return WorkflowRunRecord(
        work_item_id=str(row["work_item_id"]),
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        branch_name=str(row["branch_name"]) if row["branch_name"] is not None else None,
        pr_number=int(row["pr_number"]) if row["pr_number"] is not None else None,
        status=str(row["status"]),
        blocked_reason=str(row["blocked_reason"]) if row["blocked_reason"] is not None else None,
        last_action=str(row["last_action"]) if row["last_action"] is not None else None,
        runner_name=str(row["runner_name"]) if row["runner_name"] is not None else None,
        runner_status=str(row["runner_status"]) if row["runner_status"] is not None else None,
        outcome_status=str(row["outcome_status"]) if row["outcome_status"] is not None else None,
        outcome_summary=str(row["outcome_summary"]) if row["outcome_summary"] is not None else None,
        details={str(key): str(value) for key, value in details.items()},
        result=result,
        outcome_details=outcome_details,
        retry_count=int(row["retry_count"]) if row["retry_count"] is not None else 0,
        completed_at=str(row["completed_at"]) if row["completed_at"] is not None else None,
        updated_at=str(row["updated_at"]) if row["updated_at"] is not None else None,
    )


def mark_workflow_run_running(db_path: Path, work_item_id: str, retry_count: int = 0) -> None:
    """Write runner_status='running' immediately before blocking dispatch.

    Creates the row if it does not yet exist (first-ever run for this work item)
    so that a crashed supervisor can always detect orphaned in-flight runs by
    looking for rows where runner_status='running' and updated_at is stale.
    """
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO workflow_runs (work_item_id, status, runner_status, retry_count, updated_at)
            VALUES (?, 'ready', 'running', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(work_item_id) DO UPDATE SET
                runner_status = 'running',
                retry_count = excluded.retry_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (work_item_id, retry_count),
        )
        connection.commit()


def append_workflow_event(db_path: Path, event: WorkflowEventRecord) -> int:
    """Append an immutable event to the workflow event log. Returns the row id."""
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO workflow_events (
                work_item_id,
                action,
                runner_name,
                status,
                details_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """,
            (
                event.work_item_id,
                event.action,
                event.runner_name,
                event.status,
                json.dumps(event.details or {}, sort_keys=True),
                event.created_at,
            ),
        )
        connection.commit()
        return cursor.lastrowid or 0


def load_workflow_events(
    db_path: Path,
    work_item_id: str,
    *,
    limit: int = 100,
) -> tuple[WorkflowEventRecord, ...]:
    """Load the most recent events for a work item, newest first."""
    if limit < 1:
        raise ValueError(f"limit must be positive, got {limit}")
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                id,
                work_item_id,
                action,
                runner_name,
                status,
                details_json,
                created_at
            FROM workflow_events
            WHERE work_item_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (work_item_id, limit),
        ).fetchall()

    events: list[WorkflowEventRecord] = []
    for row in rows:
        details_payload: dict[str, str] = {}
        details_json = row["details_json"]
        if details_json:
            try:
                raw = json.loads(details_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in details_json for event {row['id']}: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"Expected dictionary for details_json, got {type(raw).__name__}")
            details_payload = {str(k): str(v) for k, v in raw.items()}
        events.append(
            WorkflowEventRecord(
                id=int(row["id"]),
                work_item_id=str(row["work_item_id"]),
                action=str(row["action"]),
                runner_name=str(row["runner_name"]) if row["runner_name"] is not None else None,
                status=str(row["status"]) if row["status"] is not None else None,
                details=details_payload,
                created_at=str(row["created_at"]) if row["created_at"] is not None else None,
            )
        )
    return tuple(events)


def append_telemetry_event(db_path: Path, event: TelemetryEventRecord) -> int:
    """Append an immutable telemetry event correlated with the active OTel trace.

    Returns the SQLite row id of the inserted record.
    """
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO telemetry_events (
                trace_id,
                span_id,
                event_type,
                component,
                run_id,
                work_item_id,
                payload_json,
                level,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """,
            (
                event.trace_id,
                event.span_id,
                event.event_type,
                event.component,
                event.run_id,
                event.work_item_id,
                json.dumps(event.payload, sort_keys=True, default=str),
                event.level,
                event.created_at,
            ),
        )
        connection.commit()
        return cursor.lastrowid or 0


def load_telemetry_events(
    db_path: Path,
    *,
    run_id: str | None = None,
    event_type: str | None = None,
    limit: int = 200,
) -> tuple[TelemetryEventRecord, ...]:
    """Load recent telemetry events, optionally filtered by run_id or event_type."""
    if limit < 1:
        raise ValueError(f"limit must be positive, got {limit}")
    initialize_database(db_path)

    conditions: list[str] = []
    params: list[object] = []
    if run_id is not None:
        conditions.append("run_id = ?")
        params.append(run_id)
    if event_type is not None:
        conditions.append("event_type = ?")
        params.append(event_type)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT
                id, trace_id, span_id, event_type, component,
                run_id, work_item_id, payload_json, level, created_at
            FROM telemetry_events
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    results: list[TelemetryEventRecord] = []
    for row in rows:
        payload: dict[str, object] = {}
        if row["payload_json"]:
            try:
                raw = json.loads(row["payload_json"])
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in telemetry payload for event {row['id']}: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"Telemetry payload must be a dict, got {type(raw).__name__}")
            payload = {str(k): v for k, v in raw.items()}
        results.append(
            TelemetryEventRecord(
                id=int(row["id"]),
                trace_id=str(row["trace_id"]) if row["trace_id"] is not None else None,
                span_id=str(row["span_id"]) if row["span_id"] is not None else None,
                event_type=str(row["event_type"]),
                component=str(row["component"]),
                run_id=str(row["run_id"]) if row["run_id"] is not None else None,
                work_item_id=str(row["work_item_id"]) if row["work_item_id"] is not None else None,
                payload=payload,
                level=str(row["level"]),
                created_at=str(row["created_at"]) if row["created_at"] is not None else None,
            )
        )
    return tuple(results)

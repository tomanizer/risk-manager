"""Minimal SQLite state store scaffold for the runtime."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
import json


SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    work_item_id TEXT PRIMARY KEY,
    branch_name TEXT,
    pr_number INTEGER,
    status TEXT NOT NULL,
    blocked_reason TEXT,
    last_action TEXT,
    runner_name TEXT,
    runner_status TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

EXPECTED_WORKFLOW_RUN_COLUMNS = (
    "work_item_id",
    "branch_name",
    "pr_number",
    "status",
    "blocked_reason",
    "last_action",
    "runner_name",
    "runner_status",
    "details_json",
    "result_json",
    "updated_at",
)

_DEFAULT_COLUMN_DEFINITIONS = {
    "last_action": "TEXT",
    "runner_name": "TEXT",
    "runner_status": "TEXT",
    "details_json": "TEXT NOT NULL DEFAULT '{}'",
    "result_json": "TEXT NOT NULL DEFAULT '{}'",
}


@dataclass(frozen=True)
class WorkflowRunRecord:
    work_item_id: str
    status: str
    branch_name: str | None = None
    pr_number: int | None = None
    blocked_reason: str | None = None
    last_action: str | None = None
    runner_name: str | None = None
    runner_status: str | None = None
    details: dict[str, str] | None = None
    result: dict[str, str] | None = None


def _verify_workflow_runs_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
    if not rows:
        raise RuntimeError("database initialization failed: workflow_runs table was not created")

    actual_columns = {row[1] for row in rows}
    missing_columns = [column for column in EXPECTED_WORKFLOW_RUN_COLUMNS if column not in actual_columns]
    if missing_columns:
        raise RuntimeError("database initialization failed: workflow_runs table is missing columns: " + ", ".join(missing_columns))


def _ensure_expected_columns(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
    actual_columns = {row[1] for row in rows}
    for column_name in EXPECTED_WORKFLOW_RUN_COLUMNS:
        if column_name in actual_columns or column_name == "updated_at":
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
        connection.commit()


def upsert_workflow_run(db_path: Path, record: WorkflowRunRecord) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO workflow_runs (
                work_item_id,
                branch_name,
                pr_number,
                status,
                blocked_reason,
                last_action,
                runner_name,
                runner_status,
                details_json,
                result_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(work_item_id) DO UPDATE SET
                branch_name = excluded.branch_name,
                pr_number = excluded.pr_number,
                status = excluded.status,
                blocked_reason = excluded.blocked_reason,
                last_action = excluded.last_action,
                runner_name = excluded.runner_name,
                runner_status = excluded.runner_status,
                details_json = excluded.details_json,
                result_json = excluded.result_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.work_item_id,
                record.branch_name,
                record.pr_number,
                record.status,
                record.blocked_reason,
                record.last_action,
                record.runner_name,
                record.runner_status,
                json.dumps(record.details or {}, sort_keys=True),
                json.dumps(record.result or {}, sort_keys=True),
            ),
        )
        connection.commit()


def load_workflow_run(db_path: Path, work_item_id: str) -> WorkflowRunRecord | None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                work_item_id,
                branch_name,
                pr_number,
                status,
                blocked_reason,
                last_action,
                runner_name,
                runner_status,
                details_json,
                result_json
            FROM workflow_runs
            WHERE work_item_id = ?
            """,
            (work_item_id,),
        ).fetchone()

    if row is None:
        return None

    details_payload = {}
    if row[8]:
        try:
            details_payload = json.loads(row[8])
        except json.JSONDecodeError:
            details_payload = {}
    result_payload = {}
    if row[9]:
        try:
            result_payload = json.loads(row[9])
        except json.JSONDecodeError:
            result_payload = {}
    details = details_payload if isinstance(details_payload, dict) else {}
    result = result_payload if isinstance(result_payload, dict) else {}
    return WorkflowRunRecord(
        work_item_id=str(row[0]),
        branch_name=str(row[1]) if row[1] is not None else None,
        pr_number=int(row[2]) if row[2] is not None else None,
        status=str(row[3]),
        blocked_reason=str(row[4]) if row[4] is not None else None,
        last_action=str(row[5]) if row[5] is not None else None,
        runner_name=str(row[6]) if row[6] is not None else None,
        runner_status=str(row[7]) if row[7] is not None else None,
        details={str(key): str(value) for key, value in details.items()},
        result={str(key): str(value) for key, value in result.items()},
    )

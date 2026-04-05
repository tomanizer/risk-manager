"""Minimal SQLite state store scaffold for the runtime."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    work_item_id TEXT PRIMARY KEY,
    branch_name TEXT,
    pr_number INTEGER,
    status TEXT NOT NULL,
    blocked_reason TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

EXPECTED_WORKFLOW_RUN_COLUMNS = (
    "work_item_id",
    "branch_name",
    "pr_number",
    "status",
    "blocked_reason",
    "updated_at",
)


def _verify_workflow_runs_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
    if not rows:
        raise RuntimeError("database initialization failed: workflow_runs table was not created")

    actual_columns = {row[1] for row in rows}
    missing_columns = [column for column in EXPECTED_WORKFLOW_RUN_COLUMNS if column not in actual_columns]
    if missing_columns:
        raise RuntimeError("database initialization failed: workflow_runs table is missing columns: " + ", ".join(missing_columns))


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        _verify_workflow_runs_schema(connection)
        connection.commit()

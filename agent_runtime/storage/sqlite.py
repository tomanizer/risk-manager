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


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()

"""SQLite-backed LangGraph checkpoint saver.

Stores checkpoint state as JSON blobs in the existing ``workflow_events``
append-only table (action=``"checkpoint"``).  This piggybacks on the same
immutable event log used for audit trails, satisfying ADR-003's trace
requirement without introducing a second persistence layer.

Usage
-----
This module is an **optional** adapter.  Import it only when ``langgraph``
is installed (``pip install "risk-manager[agent]"``).

    from agent_runtime.storage.langgraph_checkpointer import SqliteEventCheckpointer
    checkpointer = SqliteEventCheckpointer(state_db_path)
    graph = compiled_graph.with_config(checkpointer=checkpointer)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

try:
    from langgraph.checkpoint.base import (
        BaseCheckpointSaver,
        Checkpoint,
        CheckpointMetadata,
        CheckpointTuple,
    )
    from langchain_core.runnables import RunnableConfig

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False


def _require_langgraph() -> None:
    if not _LANGGRAPH_AVAILABLE:
        raise ImportError('langgraph is required for SqliteEventCheckpointer. Install it with: pip install "risk-manager[agent]"')


if _LANGGRAPH_AVAILABLE:

    class SqliteEventCheckpointer(BaseCheckpointSaver):  # type: ignore[misc]
        """LangGraph checkpoint saver backed by the workflow_events SQLite table.

        Each checkpoint is persisted as an append-only row with
        ``action='checkpoint'`` and the serialised state stored in
        ``details_json``.  The ``thread_id`` from the LangGraph config is
        stored as ``work_item_id`` so that per-WI replay is straightforward.
        """

        def __init__(self, db_path: Path) -> None:
            super().__init__()
            self._db_path = db_path
            self._ensure_table()

        def _ensure_table(self) -> None:
            from agent_runtime.storage.sqlite import initialize_database

            initialize_database(self._db_path)

        def _thread_id(self, config: RunnableConfig) -> str:
            configurable = config.get("configurable") or {}
            return str(configurable.get("thread_id") or "default")

        def _checkpoint_id(self, config: RunnableConfig) -> str | None:
            configurable = config.get("configurable") or {}
            return configurable.get("checkpoint_id")  # type: ignore[return-value]

        # ------------------------------------------------------------------
        # BaseCheckpointSaver interface
        # ------------------------------------------------------------------

        def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
            thread_id = self._thread_id(config)
            checkpoint_id = self._checkpoint_id(config)

            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                if checkpoint_id:
                    row = conn.execute(
                        """
                        SELECT id, details_json, created_at
                        FROM workflow_events
                        WHERE work_item_id = ? AND action = 'checkpoint'
                          AND json_extract(details_json, '$.checkpoint_id') = ?
                        ORDER BY id DESC LIMIT 1
                        """,
                        (thread_id, checkpoint_id),
                    ).fetchone()
                else:
                    row = conn.execute(
                        """
                        SELECT id, details_json, created_at
                        FROM workflow_events
                        WHERE work_item_id = ? AND action = 'checkpoint'
                        ORDER BY id DESC LIMIT 1
                        """,
                        (thread_id,),
                    ).fetchone()

            if row is None:
                return None

            payload = json.loads(str(row["details_json"]))
            checkpoint: Checkpoint = payload["checkpoint"]
            metadata: CheckpointMetadata = payload.get("metadata", {})
            parent_config: RunnableConfig | None = payload.get("parent_config")
            this_config: RunnableConfig = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint.get("id", str(row["id"])),
                }
            }
            return CheckpointTuple(
                config=this_config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
            )

        def list(
            self,
            config: RunnableConfig | None,
            *,
            filter: dict[str, Any] | None = None,
            before: RunnableConfig | None = None,
            limit: int | None = None,
        ) -> Iterator[CheckpointTuple]:
            thread_id = self._thread_id(config) if config else "default"
            sql = """
                SELECT id, details_json, created_at
                FROM workflow_events
                WHERE work_item_id = ? AND action = 'checkpoint'
                ORDER BY id DESC
            """
            params: list[Any] = [thread_id]
            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit)
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
            for row in rows:
                payload = json.loads(str(row["details_json"]))
                checkpoint: Checkpoint = payload["checkpoint"]
                metadata: CheckpointMetadata = payload.get("metadata", {})
                parent_config: RunnableConfig | None = payload.get("parent_config")
                this_config: RunnableConfig = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint.get("id", str(row["id"])),
                    }
                }
                yield CheckpointTuple(
                    config=this_config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config,
                )

        def put(
            self,
            config: RunnableConfig,
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: dict[str, int | str | float],
        ) -> RunnableConfig:
            thread_id = self._thread_id(config)
            checkpoint_id = checkpoint.get("id", datetime.now(UTC).isoformat())
            payload = json.dumps(
                {
                    "checkpoint_id": checkpoint_id,
                    "checkpoint": checkpoint,
                    "metadata": metadata,
                    "parent_config": config,
                    "new_versions": new_versions,
                },
                sort_keys=True,
            )
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO workflow_events (work_item_id, action, status, details_json)
                    VALUES (?, 'checkpoint', 'persisted', ?)
                    """,
                    (thread_id, payload),
                )
                conn.commit()
            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                }
            }

        def put_writes(
            self,
            config: RunnableConfig,
            writes: Sequence[tuple[str, Any]],
            task_id: str,
        ) -> None:
            thread_id = self._thread_id(config)
            payload = json.dumps({"task_id": task_id, "writes": list(writes)}, sort_keys=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO workflow_events (work_item_id, action, status, details_json)
                    VALUES (?, 'checkpoint_write', 'persisted', ?)
                    """,
                    (thread_id, payload),
                )
                conn.commit()

else:
    # Placeholder when langgraph is not installed so the module can be
    # imported without errors for type checking and tests.
    class SqliteEventCheckpointer:  # type: ignore[no-redef]
        """Stub — install langgraph to use this class."""

        def __init__(self, db_path: Path) -> None:
            _require_langgraph()

"""Structured audit event emission.

``emit_audit_event`` writes to:
1. The ``telemetry_events`` SQLite table (durable, queryable, correlated with
   the active OTel trace/span when available).
2. The structlog / stdlib logger for the calling component (machine-readable
   JSON when structlog is installed).

Both sinks are best-effort — a write failure in one does not prevent the
other from succeeding, and neither raises into application code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alterraflow.telemetry._compat import get_logger
from alterraflow.telemetry.spans import current_trace_context

_log = get_logger(__name__)


def emit_audit_event(
    db_path: Path,
    event_type: str,
    component: str,
    payload: dict[str, object],
    *,
    run_id: str | None = None,
    work_item_id: str | None = None,
    level: str = "INFO",
) -> None:
    """Emit a structured audit event to SQLite and the log sink.

    Parameters
    ----------
    db_path:
        Path to the SQLite state database.
    event_type:
        Short machine-readable event name, e.g. ``"runner.dispatch.started"``.
    component:
        Dotted component identifier, e.g. ``"alterraflow.orchestrator"``.
    payload:
        Arbitrary structured data for this event.
    run_id:
        Optional run identifier to correlate with ``workflow_runs``.
    work_item_id:
        Optional work-item identifier.
    level:
        Log level string: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
    """
    trace_id, span_id = current_trace_context()

    _write_sqlite(
        db_path=db_path,
        trace_id=trace_id,
        span_id=span_id,
        event_type=event_type,
        component=component,
        run_id=run_id,
        work_item_id=work_item_id,
        payload=payload,
        level=level,
    )

    _write_log(
        event_type=event_type,
        component=component,
        payload=payload,
        run_id=run_id,
        work_item_id=work_item_id,
        trace_id=trace_id,
        span_id=span_id,
        level=level,
    )


# ---------------------------------------------------------------------------
# Internal sinks
# ---------------------------------------------------------------------------


def _write_sqlite(
    *,
    db_path: Path,
    trace_id: str | None,
    span_id: str | None,
    event_type: str,
    component: str,
    run_id: str | None,
    work_item_id: str | None,
    payload: dict[str, object],
    level: str,
) -> None:
    try:
        from alterraflow.storage.sqlite import TelemetryEventRecord, append_telemetry_event

        append_telemetry_event(
            db_path,
            TelemetryEventRecord(
                trace_id=trace_id,
                span_id=span_id,
                event_type=event_type,
                component=component,
                run_id=run_id,
                work_item_id=work_item_id,
                payload=payload,
                level=level,
            ),
        )
    except Exception as exc:
        _log.warning("audit_sqlite_write_failed", event_type=event_type, error=str(exc))


def _write_log(
    *,
    event_type: str,
    component: str,
    payload: dict[str, object],
    run_id: str | None,
    work_item_id: str | None,
    trace_id: str | None,
    span_id: str | None,
    level: str,
) -> None:
    try:
        log = get_logger(f"audit.{component}")
        kw: dict[str, Any] = {
            **{str(k): v for k, v in payload.items()},
            "component": component,
        }
        if run_id is not None:
            kw["run_id"] = run_id
        if work_item_id is not None:
            kw["work_item_id"] = work_item_id
        if trace_id is not None:
            kw["trace_id"] = trace_id
        if span_id is not None:
            kw["span_id"] = span_id

        log_fn = getattr(log, level.lower(), log.info)
        log_fn(event_type, **kw)
    except Exception as exc:
        _log.warning("audit_log_write_failed", event_type=event_type, error=str(exc))

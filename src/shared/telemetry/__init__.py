"""Cross-cutting telemetry helpers for ``src`` (logging; trace context; timing).

Independent of ``agent_runtime``. Configure handlers on :data:`LOGGER_NAME`.

See ``docs/shared_infra/telemetry.md``.
"""

from __future__ import annotations

from .operation_log import (
    EVENT_NAME,
    LOGGER_NAME,
    StdlibLoggerAdapter,
    configure_operation_logging,
    current_trace_context,
    duration_ms,
    emit_operation,
    iso_date,
    node_ref_log_dict,
    reset_operation_logging_to_defaults,
    status_string,
    timer_start,
)

__all__ = [
    "EVENT_NAME",
    "LOGGER_NAME",
    "StdlibLoggerAdapter",
    "configure_operation_logging",
    "current_trace_context",
    "duration_ms",
    "emit_operation",
    "iso_date",
    "node_ref_log_dict",
    "reset_operation_logging_to_defaults",
    "status_string",
    "timer_start",
]

"""Shared structured operation logging for `src/` modules.

Aligned with `docs/shared_infra/telemetry.md` and design patterns from
`agent_runtime/telemetry` (stdlib-first, level gating, no ``agent_runtime``
imports). A configured structlog logger may be injected via
:func:`configure_operation_logging`.

Handlers attach to :data:`LOGGER_NAME` via ``logging.getLogger(...)``.
"""

from __future__ import annotations

import logging
import os
import time as perf_time
from datetime import date
from enum import Enum
from typing import Any, cast

from src.shared import ServiceError

DEFAULT_EVENT_NAME = "operation"

_LOGGER_NAME_RAW = os.getenv("SRC_TELEMETRY_LOGGER_NAME", "").strip()
LOGGER_NAME = _LOGGER_NAME_RAW or "src.shared.telemetry"

_EVENT_NAME_RAW = os.getenv("SRC_TELEMETRY_EVENT_NAME", "").strip()
EVENT_NAME = _EVENT_NAME_RAW or DEFAULT_EVENT_NAME

_INFO_STATUSES = {"OK", "PARTIAL", "MISSING_COMPARE"}
_WARNING_STATUSES = {"MISSING_HISTORY", "DEGRADED", "MISSING_SNAPSHOT", "MISSING_NODE", "UNSUPPORTED_MEASURE"}


class StdlibLoggerAdapter:
    """structlog-style surface backed by stdlib ``logging`` (handlers, levels, filters)."""

    def __init__(self, name: str, bound_context: dict[str, object] | None = None) -> None:
        self._log = logging.getLogger(name)
        self._bound_context = dict(bound_context or {})

    def _structured_event(self, **kw: object) -> dict[str, object]:
        if not self._bound_context:
            return dict(kw)
        merged: dict[str, object] = dict(self._bound_context)
        merged.update(kw)
        return merged

    def debug(self, event: str, **kw: object) -> None:
        self._log.debug(event, extra={"structured_event": self._structured_event(**kw)})

    def info(self, event: str, **kw: object) -> None:
        self._log.info(event, extra={"structured_event": self._structured_event(**kw)})

    def warning(self, event: str, **kw: object) -> None:
        self._log.warning(event, extra={"structured_event": self._structured_event(**kw)})

    def error(self, event: str, **kw: object) -> None:
        self._log.error(event, extra={"structured_event": self._structured_event(**kw)})

    def exception(self, event: str, **kw: object) -> None:
        self._log.exception(event, extra={"structured_event": self._structured_event(**kw)})

    def bind(self, **kw: object) -> "StdlibLoggerAdapter":
        if not kw:
            return StdlibLoggerAdapter(self._log.name, dict(self._bound_context))
        merged = dict(self._bound_context)
        merged.update(kw)
        return StdlibLoggerAdapter(self._log.name, merged)

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802
        return self._log.isEnabledFor(level)


def _env_enabled() -> bool:
    return os.getenv("SRC_TELEMETRY_ENABLED", "1").strip().lower() not in {"0", "false", "off", "no"}


def _build_default_logger() -> Any:
    """Default to stdlib so levels and handlers on ``logging.getLogger(LOGGER_NAME)`` apply."""
    return StdlibLoggerAdapter(LOGGER_NAME)


_enabled = _env_enabled()
_log: Any = _build_default_logger()


def configure_operation_logging(*, enabled: bool | None = None, logger: Any | None = None) -> None:
    """Runtime toggle and optional logger injection (tests, custom sinks)."""
    # pylint: disable=global-statement
    global _enabled, _log
    if enabled is not None:
        _enabled = enabled
    if logger is not None:
        _log = logger


def reset_operation_logging_to_defaults() -> None:
    """Restore module defaults (e.g. after tests patch global state)."""
    # pylint: disable=global-statement
    global _enabled, _log
    _enabled = _env_enabled()
    _log = _build_default_logger()


def status_string(outcome: Any) -> str:
    if isinstance(outcome, ServiceError):
        return outcome.status_code
    return cast(str, outcome.status.value)


def canonical_terminal_run_status_status(terminal_status: str | Enum) -> str:
    """Map PRD terminal run statuses to shared canonical telemetry statuses.

    Degrades gracefully on unrecognised values: logs a warning and returns
    ``"DEGRADED"`` so that a future TerminalRunStatus addition never crashes
    an otherwise complete orchestrator run.  Contract coverage is verified by
    the exhaustive test in ``tests/unit/shared/telemetry/test_operation_log.py``.
    """
    terminal_status_value = terminal_status.value if isinstance(terminal_status, Enum) else terminal_status
    mapping = {
        "COMPLETED": "OK",
        "COMPLETED_WITH_CAVEATS": "DEGRADED",
        "COMPLETED_WITH_FAILURES": "PARTIAL",
        "FAILED_ALL_TARGETS": "DEGRADED",
        "BLOCKED_READINESS": "DEGRADED",
    }
    result = mapping.get(terminal_status_value)
    if result is None:
        if _should_emit("DEGRADED"):
            _log.warning(
                EVENT_NAME,
                operation="canonical_terminal_run_status_status",
                status="DEGRADED",
                duration_ms=0,
                unrecognised_terminal_status=str(terminal_status_value),
            )
        return "DEGRADED"
    return result


def node_ref_log_dict(node_ref: Any) -> dict[str, str | None]:
    """Serialize a scope-aware node reference for structured logs (risk analytics shape)."""
    return {
        "node_id": node_ref.node_id,
        "node_level": node_ref.node_level.value,
        "hierarchy_scope": node_ref.hierarchy_scope.value,
        "legal_entity_id": node_ref.legal_entity_id,
    }


def timer_start() -> float:
    return perf_time.monotonic()


def duration_ms(start_time: float) -> int:
    elapsed = (perf_time.monotonic() - start_time) * 1000.0
    return max(0, int(round(elapsed)))


def iso_date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def current_trace_context() -> tuple[str | None, str | None]:
    """Return ``(trace_id_hex, span_id_hex)`` when OpenTelemetry context is active."""
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:
        pass
    return None, None


def _normalize_context_value(value: Any) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_normalize_context_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _normalize_context_value(v) for k, v in value.items()}
    raise TypeError(f"unsupported log context type: {type(value)!r}")


def _normalize_context_value_for_emit(value: Any) -> object:
    """Normalize context for emission; never raises (unsupported values become a short placeholder)."""
    try:
        if isinstance(value, dict):
            return {str(k): _normalize_context_value_for_emit(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_normalize_context_value_for_emit(v) for v in value]
        return _normalize_context_value(value)
    except TypeError:
        return f"<unserializable:{type(value).__name__}>"


def _status_level(status: str) -> int:
    if status in _INFO_STATUSES:
        return logging.INFO
    if status in _WARNING_STATUSES:
        return logging.WARNING
    return logging.WARNING


def _should_emit(status: str) -> bool:
    if not _enabled:
        return False
    is_enabled_for = getattr(_log, "isEnabledFor", None)
    if callable(is_enabled_for):
        return bool(is_enabled_for(_status_level(status)))
    return True


def emit_operation(
    operation: str,
    *,
    status: str,
    start_time: float,
    include_trace_context: bool = True,
    **context: Any,
) -> None:
    """Emit one structured record for a completed operation.

    ``context`` values are normalized (dates → ISO strings, enums → ``.value``,
    dicts and sequences recursively). Unsupported leaf values become a short
    ``<unserializable:...>`` placeholder so emission never raises. Callers pass
    domain fields explicitly (for example ``node_ref=node_ref_log_dict(ref)``).
    """
    if not _should_emit(status):
        return

    payload: dict[str, object] = {
        "operation": operation,
        "status": status,
        "duration_ms": duration_ms(start_time),
    }
    if include_trace_context:
        trace_id, span_id = current_trace_context()
        payload["trace_id"] = trace_id
        payload["span_id"] = span_id
    for key, val in context.items():
        payload[key] = _normalize_context_value_for_emit(val)

    if status in _INFO_STATUSES:
        _log.info(EVENT_NAME, **payload)
        return
    if status in _WARNING_STATUSES:
        _log.warning(EVENT_NAME, **payload)
        return
    _log.warning(EVENT_NAME, **payload)

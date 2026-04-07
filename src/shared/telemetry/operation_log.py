"""Shared structured operation logging for `src/` modules.

Aligned with `docs/shared_infra/telemetry.md` and design patterns from
`agent_runtime/telemetry` (stdlib + optional structlog, level gating, no
`agent_runtime` imports).

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

try:
    import structlog
except ImportError:
    structlog = None

DEFAULT_EVENT_NAME = "operation"

_LOGGER_NAME_RAW = os.getenv("SRC_TELEMETRY_LOGGER_NAME", "").strip()
LOGGER_NAME = _LOGGER_NAME_RAW or "src.shared.telemetry"

_EVENT_NAME_RAW = os.getenv("SRC_TELEMETRY_EVENT_NAME", "").strip()
EVENT_NAME = _EVENT_NAME_RAW or DEFAULT_EVENT_NAME

_INFO_STATUSES = {"OK", "PARTIAL", "MISSING_COMPARE"}
_WARNING_STATUSES = {"MISSING_HISTORY", "DEGRADED", "MISSING_SNAPSHOT", "MISSING_NODE", "UNSUPPORTED_MEASURE"}


class StdlibLoggerAdapter:
    """structlog-style surface backed by stdlib ``logging`` (handlers, levels, filters)."""

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def debug(self, event: str, **kw: object) -> None:
        self._log.debug(event, extra={"structured_event": kw})

    def info(self, event: str, **kw: object) -> None:
        self._log.info(event, extra={"structured_event": kw})

    def warning(self, event: str, **kw: object) -> None:
        self._log.warning(event, extra={"structured_event": kw})

    def error(self, event: str, **kw: object) -> None:
        self._log.error(event, extra={"structured_event": kw})

    def exception(self, event: str, **kw: object) -> None:
        self._log.exception(event, extra={"structured_event": kw})

    def bind(self, **kw: object) -> "StdlibLoggerAdapter":
        del kw
        return self

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802
        return self._log.isEnabledFor(level)


def _env_enabled() -> bool:
    return os.getenv("SRC_TELEMETRY_ENABLED", "1").strip().lower() not in {"0", "false", "off", "no"}


def _build_default_logger() -> Any:
    if structlog is not None:
        return structlog.get_logger(LOGGER_NAME)
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
    if isinstance(value, dict):
        return {str(k): _normalize_context_value(v) for k, v in value.items()}
    raise TypeError(f"unsupported log context type: {type(value)!r}")


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
    shallow dicts recursively). Callers pass domain fields explicitly
    (for example ``node_ref=node_ref_log_dict(ref)``).
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
        payload[key] = _normalize_context_value(val)

    if status in _INFO_STATUSES:
        _log.info(EVENT_NAME, **payload)
        return
    if status in _WARNING_STATUSES:
        _log.warning(EVENT_NAME, **payload)
        return
    _log.warning(EVENT_NAME, **payload)

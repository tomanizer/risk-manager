"""Compatibility shims: graceful degradation when OTel / structlog are absent."""

from __future__ import annotations

import logging
from typing import Any

try:
    import structlog as _structlog

    _STRUCTLOG_AVAILABLE = True
except ImportError:
    _STRUCTLOG_AVAILABLE = False

try:
    from opentelemetry import trace as _otel_trace  # noqa: F401
    from opentelemetry import metrics as _otel_metrics  # noqa: F401

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False


class _StdlibLoggerAdapter:
    """structlog-compatible logger backed by stdlib logging.

    Accepts keyword-argument style calls so callers can use the same API
    regardless of whether structlog is installed.
    """

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def _format(self, event: str, kw: dict[str, object]) -> str:
        if kw:
            ctx = " ".join(f"{k}={v!r}" for k, v in kw.items())
            return f"{event} {ctx}"
        return event

    def debug(self, event: str, **kw: object) -> None:
        self._log.debug(self._format(event, kw))

    def info(self, event: str, **kw: object) -> None:
        self._log.info(self._format(event, kw))

    def warning(self, event: str, **kw: object) -> None:
        self._log.warning(self._format(event, kw))

    def error(self, event: str, **kw: object) -> None:
        self._log.error(self._format(event, kw))

    def exception(self, event: str, **kw: object) -> None:
        self._log.exception(self._format(event, kw))

    def bind(self, **kw: object) -> "_StdlibLoggerAdapter":
        return self


def get_logger(name: str = __name__) -> Any:
    """Return a structlog logger or a stdlib-backed adapter."""
    if _STRUCTLOG_AVAILABLE:
        return _structlog.get_logger(name)
    return _StdlibLoggerAdapter(name)


def is_otel_available() -> bool:
    return _OTEL_AVAILABLE


def is_structlog_available() -> bool:
    return _STRUCTLOG_AVAILABLE

"""Span helpers and decorators for OTel instrumentation.

All public symbols degrade gracefully to no-ops when ``opentelemetry``
is not installed.
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

from alterraflow.telemetry._compat import _OTEL_AVAILABLE

_F = TypeVar("_F", bound=Callable[..., Any])

_INSTRUMENTATION_NAME = "alterraflow"


def _get_tracer(component: str = _INSTRUMENTATION_NAME) -> Any:
    if not _OTEL_AVAILABLE:
        return None
    from opentelemetry import trace

    return trace.get_tracer(component)


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def traced(
    span_name: str,
    component: str = _INSTRUMENTATION_NAME,
    **static_attrs: str,
) -> Callable[[_F], _F]:
    """Wrap a function in an OTel span.

    Sets ``error.type`` and records the exception on unhandled errors.
    Is a no-op when OTel is not installed.
    """

    def decorator(fn: _F) -> _F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _OTEL_AVAILABLE:
                return fn(*args, **kwargs)
            from opentelemetry.trace import Status, StatusCode

            tracer = _get_tracer(component)
            with tracer.start_as_current_span(span_name) as span:
                for k, v in static_attrs.items():
                    span.set_attribute(k, v)
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    span.set_attribute("error.type", type(exc).__name__)
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------


@contextmanager
def workflow_span(
    action: str,
    *,
    run_id: str | None = None,
    work_item_id: str | None = None,
    runner_name: str | None = None,
    component: str = "alterraflow.orchestrator",
) -> Generator[Any, None, None]:
    """Context manager that opens an OTel span for one orchestration step."""
    if not _OTEL_AVAILABLE:
        yield None
        return

    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    tracer = trace.get_tracer(component)
    with tracer.start_as_current_span(f"workflow.{action}") as span:
        span.set_attribute("workflow.action", action)
        if run_id is not None:
            span.set_attribute("workflow.run_id", run_id)
        if work_item_id is not None:
            span.set_attribute("workflow.work_item_id", work_item_id)
        if runner_name is not None:
            span.set_attribute("workflow.runner_name", runner_name)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@contextmanager
def runner_span(
    runner_name: str,
    work_item_id: str,
    *,
    run_id: str | None = None,
    component: str = "alterraflow.runners",
) -> Generator[Any, None, None]:
    """Context manager that opens an OTel span for a single runner dispatch."""
    if not _OTEL_AVAILABLE:
        yield None
        return

    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    tracer = trace.get_tracer(component)
    with tracer.start_as_current_span(f"runner.{runner_name}") as span:
        span.set_attribute("runner.name", runner_name)
        span.set_attribute("runner.work_item_id", work_item_id)
        if run_id is not None:
            span.set_attribute("runner.run_id", run_id)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@contextmanager
def risk_service_span(
    node_ref: str,
    measure_type: str,
    start_date: str,
    end_date: str,
    *,
    component: str = "src.modules.risk_analytics",
) -> Generator[Any, None, None]:
    """Context manager that opens an OTel span for a risk service call."""
    if not _OTEL_AVAILABLE:
        yield None
        return

    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    tracer = trace.get_tracer(component)
    with tracer.start_as_current_span("risk_analytics.get_risk_history") as span:
        span.set_attribute("risk.node_ref", node_ref)
        span.set_attribute("risk.measure_type", measure_type)
        span.set_attribute("risk.start_date", start_date)
        span.set_attribute("risk.end_date", end_date)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@contextmanager
def drift_scan_span(
    scan_name: str,
    *,
    component: str = "alterraflow.drift",
) -> Generator[Any, None, None]:
    """Context manager that opens an OTel span for one drift scanner."""
    if not _OTEL_AVAILABLE:
        yield None
        return

    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    tracer = trace.get_tracer(component)
    with tracer.start_as_current_span(f"drift.{scan_name}") as span:
        span.set_attribute("drift.scan_name", scan_name)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


# ---------------------------------------------------------------------------
# Utility: current trace/span context for audit correlation
# ---------------------------------------------------------------------------


def current_trace_context() -> tuple[str | None, str | None]:
    """Return (trace_id_hex, span_id_hex) of the active span, or (None, None)."""
    if not _OTEL_AVAILABLE:
        return None, None
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:
        pass
    return None, None


def elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since ``start`` (from ``time.monotonic()``)."""
    return (time.monotonic() - start) * 1000.0

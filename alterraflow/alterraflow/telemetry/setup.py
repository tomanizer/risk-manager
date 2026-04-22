"""OTel SDK + structlog initialisation.

Call ``configure_telemetry()`` once at process startup, before any
instrumented code runs.  The function is safe to call when the optional
``telemetry`` extras are not installed — it will configure structlog
(using a JSON renderer if available, otherwise stdlib) and return False.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from alterraflow.telemetry._compat import _OTEL_AVAILABLE, _STRUCTLOG_AVAILABLE

_DEFAULT_SERVICE_NAME = "risk-manager-agent-runtime"
_DEFAULT_OTLP_ENDPOINT = "http://localhost:4318"
_DEFAULT_PROMETHEUS_PORT = 9464


def configure_telemetry(
    service_name: str = _DEFAULT_SERVICE_NAME,
    otlp_endpoint: str | None = None,
    enable_prometheus_port: int | None = _DEFAULT_PROMETHEUS_PORT,
    log_level: str = "INFO",
) -> bool:
    """Configure OTel SDK and structlog.

    Parameters
    ----------
    service_name:
        OTel ``service.name`` resource attribute.
    otlp_endpoint:
        Base URL of the OTLP HTTP receiver (e.g. ``http://localhost:4318``).
        Defaults to ``OTEL_EXPORTER_OTLP_ENDPOINT`` env var, then
        ``http://localhost:4318``.
    enable_prometheus_port:
        If set, start an HTTP server on this port exposing ``/metrics``
        for Prometheus scraping.  Set to ``None`` to disable.
    log_level:
        Root log level string, e.g. ``"INFO"`` or ``"DEBUG"``.

    Returns
    -------
    bool
        ``True`` if OTel SDK was fully configured, ``False`` if the
        ``telemetry`` extras are not installed (structlog still
        configured if available).
    """
    _configure_stdlib_logging(log_level)
    _configure_structlog()
    if not _OTEL_AVAILABLE:
        return False
    _configure_otel(service_name, otlp_endpoint, enable_prometheus_port)
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _configure_stdlib_logging(log_level: str) -> None:
    numeric = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=numeric, format="%(levelname)s %(name)s %(message)s")


def _configure_structlog() -> None:
    if not _STRUCTLOG_AVAILABLE:
        return
    import structlog

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if _OTEL_AVAILABLE:
        try:
            from opentelemetry import trace

            def _add_otel_context(
                logger: Any,
                method: str,
                event_dict: dict[str, Any],
            ) -> dict[str, Any]:
                span = trace.get_current_span()
                ctx = span.get_span_context()
                if ctx.is_valid:
                    event_dict["trace_id"] = format(ctx.trace_id, "032x")
                    event_dict["span_id"] = format(ctx.span_id, "016x")
                return event_dict

            shared_processors.append(_add_otel_context)
        except Exception:
            pass

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _configure_otel(
    service_name: str,
    otlp_endpoint: str | None,
    enable_prometheus_port: int | None,
) -> None:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    resource = Resource.create({"service.name": service_name})

    # --- Traces ---
    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", _DEFAULT_OTLP_ENDPOINT)
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        span_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)
    except Exception:
        # If OTLP export fails (e.g. collector not running), use noop provider.
        pass

    # --- Metrics ---
    metric_readers: list[Any] = []

    if enable_prometheus_port is not None:
        try:
            from opentelemetry.exporter.prometheus import PrometheusMetricReader

            # PrometheusMetricReader starts its own HTTP server on the given port.
            metric_readers.append(PrometheusMetricReader(port=enable_prometheus_port))
        except Exception:
            pass

    try:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

        metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
        metric_readers.append(PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15_000))
    except Exception:
        pass

    if metric_readers:
        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)

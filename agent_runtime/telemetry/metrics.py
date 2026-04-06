"""OTel metric instruments for the agent runtime.

All instruments degrade to no-ops when ``opentelemetry`` is not installed.
Instruments are created lazily on first use so that the module can be
imported freely without requiring the SDK to be initialised first.
"""

from __future__ import annotations

import time
from typing import Any

from agent_runtime.telemetry._compat import _OTEL_AVAILABLE

_METER_NAME = "agent_runtime"

# Module-level cache — populated on first access.
_meter: Any = None
_workflow_runs_counter: Any = None
_runner_dispatches_counter: Any = None
_runner_duration_histogram: Any = None
_risk_service_duration_histogram: Any = None
_risk_service_calls_counter: Any = None
_supervisor_heartbeat_gauge: Any = None
_drift_checks_counter: Any = None


def _get_meter() -> Any:
    global _meter
    if _meter is None and _OTEL_AVAILABLE:
        from opentelemetry import metrics

        _meter = metrics.get_meter(_METER_NAME)
    return _meter


def _workflow_runs() -> Any:
    global _workflow_runs_counter
    if _workflow_runs_counter is None:
        meter = _get_meter()
        if meter is not None:
            _workflow_runs_counter = meter.create_counter(
                "workflow_runs_total",
                description="Total orchestration steps taken by the supervisor loop.",
                unit="1",
            )
    return _workflow_runs_counter


def _runner_dispatches() -> Any:
    global _runner_dispatches_counter
    if _runner_dispatches_counter is None:
        meter = _get_meter()
        if meter is not None:
            _runner_dispatches_counter = meter.create_counter(
                "runner_dispatches_total",
                description="Total runner invocations dispatched.",
                unit="1",
            )
    return _runner_dispatches_counter


def _runner_duration() -> Any:
    global _runner_duration_histogram
    if _runner_duration_histogram is None:
        meter = _get_meter()
        if meter is not None:
            _runner_duration_histogram = meter.create_histogram(
                "runner_duration_seconds",
                description="Wall-clock duration of runner dispatches.",
                unit="s",
            )
    return _runner_duration_histogram


def _risk_service_duration() -> Any:
    global _risk_service_duration_histogram
    if _risk_service_duration_histogram is None:
        meter = _get_meter()
        if meter is not None:
            _risk_service_duration_histogram = meter.create_histogram(
                "risk_service_duration_seconds",
                description="Wall-clock duration of get_risk_history calls.",
                unit="s",
            )
    return _risk_service_duration_histogram


def _risk_service_calls() -> Any:
    global _risk_service_calls_counter
    if _risk_service_calls_counter is None:
        meter = _get_meter()
        if meter is not None:
            _risk_service_calls_counter = meter.create_counter(
                "risk_service_calls_total",
                description="Total get_risk_history calls by outcome status.",
                unit="1",
            )
    return _risk_service_calls_counter


def _drift_checks() -> Any:
    global _drift_checks_counter
    if _drift_checks_counter is None:
        meter = _get_meter()
        if meter is not None:
            _drift_checks_counter = meter.create_counter(
                "drift_checks_total",
                description="Total drift findings observed per scanner and severity.",
                unit="1",
            )
    return _drift_checks_counter


def _heartbeat_gauge() -> Any:
    global _supervisor_heartbeat_gauge
    if _supervisor_heartbeat_gauge is None:
        meter = _get_meter()
        if meter is not None:
            _supervisor_heartbeat_gauge = meter.create_observable_gauge(
                "supervisor_heartbeat_age_seconds",
                description="Seconds since the last supervisor heartbeat was written.",
                unit="s",
            )
    return _supervisor_heartbeat_gauge


# ---------------------------------------------------------------------------
# Public recording helpers
# ---------------------------------------------------------------------------

# Tracks the last heartbeat timestamp so the observable gauge can compute age.
_last_heartbeat_ts: float | None = None


def record_workflow_action(action: str, status: str = "ok") -> None:
    """Increment the workflow step counter."""
    counter = _workflow_runs()
    if counter is not None:
        counter.add(1, {"action": action, "status": status})


def record_runner_dispatch(
    runner_name: str,
    outcome_status: str,
    duration_seconds: float,
) -> None:
    """Record a completed runner dispatch (counter + histogram)."""
    counter = _runner_dispatches()
    if counter is not None:
        counter.add(1, {"runner_name": runner_name, "outcome_status": outcome_status})
    hist = _runner_duration()
    if hist is not None:
        hist.record(duration_seconds, {"runner_name": runner_name})


def record_risk_service_call(status: str, duration_seconds: float) -> None:
    """Record a completed risk service call (histogram + counter)."""
    hist = _risk_service_duration()
    if hist is not None:
        hist.record(duration_seconds, {"status": status})
    counter = _risk_service_calls()
    if counter is not None:
        counter.add(1, {"status": status})


def record_drift_findings(scan_name: str, severity: str, count: int = 1) -> None:
    """Increment the drift findings counter."""
    counter = _drift_checks()
    if counter is not None:
        counter.add(count, {"scan_name": scan_name, "severity": severity})


def update_heartbeat_timestamp() -> None:
    """Record that a supervisor heartbeat just occurred."""
    global _last_heartbeat_ts
    _last_heartbeat_ts = time.monotonic()

    # Eagerly register the observable gauge callback on first heartbeat.
    meter = _get_meter()
    if meter is None:
        return
    global _supervisor_heartbeat_gauge
    if _supervisor_heartbeat_gauge is None:

        def _observe_age(options: Any) -> list[Any]:
            from opentelemetry.metrics import Observation

            if _last_heartbeat_ts is None:
                return []
            age = time.monotonic() - _last_heartbeat_ts
            return [Observation(age)]

        _supervisor_heartbeat_gauge = meter.create_observable_gauge(
            "supervisor_heartbeat_age_seconds",
            callbacks=[_observe_age],
            description="Seconds since the last supervisor heartbeat was written.",
            unit="s",
        )

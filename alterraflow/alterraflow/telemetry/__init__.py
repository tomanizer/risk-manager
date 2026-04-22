"""Telemetry module for the risk-manager agent runtime.

Public API
----------
configure_telemetry   -- initialise OTel SDK + structlog at process start
get_logger            -- return a structlog / stdlib logger
is_otel_available     -- True when opentelemetry packages are installed
is_structlog_available -- True when structlog is installed

workflow_span         -- OTel span context manager for orchestration steps
runner_span           -- OTel span context manager for runner dispatches
risk_service_span     -- OTel span context manager for risk service calls
drift_scan_span       -- OTel span context manager for drift scanner runs
traced                -- decorator that wraps any function in a span

record_workflow_action    -- increment workflow step counter
record_runner_dispatch    -- record runner counter + duration histogram
record_risk_service_call  -- record risk service counter + duration histogram
record_drift_findings     -- increment drift findings counter
update_heartbeat_timestamp -- note that a supervisor heartbeat occurred

emit_audit_event      -- write a structured audit event to SQLite + log sink
"""

from alterraflow.telemetry._compat import get_logger, is_otel_available, is_structlog_available
from alterraflow.telemetry.audit import emit_audit_event
from alterraflow.telemetry.metrics import (
    record_drift_findings,
    record_risk_service_call,
    record_runner_dispatch,
    record_workflow_action,
    update_heartbeat_timestamp,
)
from alterraflow.telemetry.setup import configure_telemetry
from alterraflow.telemetry.spans import (
    current_trace_context,
    drift_scan_span,
    risk_service_span,
    runner_span,
    traced,
    workflow_span,
)

__all__ = [
    "configure_telemetry",
    "get_logger",
    "is_otel_available",
    "is_structlog_available",
    "workflow_span",
    "runner_span",
    "risk_service_span",
    "drift_scan_span",
    "traced",
    "current_trace_context",
    "record_workflow_action",
    "record_runner_dispatch",
    "record_risk_service_call",
    "record_drift_findings",
    "update_heartbeat_timestamp",
    "emit_audit_event",
]

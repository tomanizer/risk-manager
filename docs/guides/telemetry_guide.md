# Telemetry Guide

## Purpose

This guide covers the telemetry layer added to the risk-manager agent runtime.
It explains what is collected, where it goes, how to start the local visualization
stack, and how to extend the system with new instrumentation.

---

## What is collected and why

| Signal | Where | Purpose |
|--------|-------|---------|
| **Distributed traces** (spans) | OTel → Jaeger | Reconstruct the exact sequence of operations for a workflow run — supervisor tick, runner dispatch, drift scan |
| **Metrics** (counters + histograms) | OTel → Prometheus | Track aggregate health: step rate, runner latency, risk call outcomes, supervisor liveness |
| **Structured audit log** | SQLite `telemetry_events` + structlog | Append-only, queryable record of instrumented runtime events such as runner dispatches; correlated with active OTel trace/span |

All three signals are optional. The runtime degrades gracefully when the
`telemetry` extras are not installed — all wrappers become no-ops and stdlib
logging is used as a fallback.

---

## Quick start

### 1. Install the telemetry extras

```bash
pip install -e ".[telemetry]"
```

This installs:

- `opentelemetry-api` / `opentelemetry-sdk` — core OTel SDK
- `opentelemetry-exporter-otlp-proto-http` — ships traces and metrics to Jaeger
- `opentelemetry-exporter-prometheus` — exposes `/metrics` for Prometheus scraping
- `structlog` — structured JSON logging

### 2. Start the visualization stack

```bash
docker compose -f docker-compose.observability.yml up -d
```

| Service | URL | What you see |
|---------|-----|-------------|
| Jaeger | <http://localhost:16686> | Per-run distributed traces, span timelines |
| Prometheus | <http://localhost:9090> | Raw metric time-series, PromQL explorer |
| Grafana | <http://localhost:3000> | Pre-built dashboards (admin / admin) |

### 3. Run the agent runtime

```bash
python -m agent_runtime --poll
```

Telemetry is configured automatically in `main()`. Spans are sent to Jaeger at
`http://localhost:4318`, metrics are scraped by Prometheus from
`http://localhost:9464/metrics`.

---

## Architecture

```text
agent_runtime/               src/modules/
orchestrator/graph.py        risk_analytics/service.py (*)
runners/dispatch.py
drift/drift_suite.py
       │
       ▼
agent_runtime/telemetry/
  setup.py   — OTel SDK + structlog init
  spans.py   — span context managers and @traced decorator
  metrics.py — counters and histograms
  audit.py   — audit event → SQLite + structlog
       │                    │
       ▼                    ▼
OTLP HTTP export      SQLite telemetry_events
  → Jaeger               table in .agent_runtime/state.db
  → Prometheus
  → Grafana
```

> (*) The `src/modules/` domain code does not import `agent_runtime.telemetry`
> because modules must remain free of runtime dependencies
> (see architecture boundary rule). Risk service telemetry should be added in
> a walker layer when walkers are implemented.

---

## Metrics reference

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `workflow_runs_total` | Counter | `action`, `status` | One increment per orchestration step |
| `runner_dispatches_total` | Counter | `runner_name`, `outcome_status` | Completed runner invocations |
| `runner_duration_seconds` | Histogram | `runner_name` | Wall-clock time of each runner dispatch |
| `risk_service_duration_seconds` | Histogram | `status` | Duration of `get_risk_history` calls (walker layer, future) |
| `risk_service_calls_total` | Counter | `status` | Risk service call outcomes (walker layer, future) |
| `supervisor_heartbeat_age_seconds` | Observable Gauge | — | Seconds since the last supervisor heartbeat |
| `drift_checks_total` | Counter | `scan_name`, `severity` | Net-new drift findings per scanner per severity |

---

## Traces reference

| Span name | Component | Key attributes |
|-----------|-----------|---------------|
| `workflow.runner_dispatch` | `agent_runtime.orchestrator` | `workflow.action`, `workflow.run_id`, `workflow.work_item_id`, `workflow.runner_name` |
| `runner.<name>` | `agent_runtime.runners` | `runner.name`, `runner.work_item_id`, `runner.run_id`, `runner.outcome_status` |
| `drift.<scan_name>` | `agent_runtime.drift` | `drift.scan_name`, `drift.total_findings`, `drift.new_findings` |
| `risk_analytics.get_risk_history` | `src.modules.risk_analytics` | `risk.node_ref`, `risk.measure_type`, `risk.start_date`, `risk.end_date`, `risk.result_status`, `risk.points_returned` |

---

## Audit events reference

Current audit-table coverage is intentionally narrow: the runtime persists
runner dispatch start/completion events, and additional event families should be
documented only after they are wired in code.

Audit events are written to:

1. **`telemetry_events` table** in `state.db` — queryable with DuckDB or any SQLite client;
   correlated with the active OTel trace via `trace_id` and `span_id` columns.
2. **structlog JSON output** — stdout when running interactively, or redirect to
   a file with `python -m agent_runtime --poll 2>logs/agent.jsonl`.

| Event type | Component | When |
|------------|-----------|------|
| `runner.dispatch.started` | `agent_runtime.runners.dispatch` | Immediately before each runner execution |
| `runner.dispatch.completed` | `agent_runtime.runners.dispatch` | After each runner execution, with `runner_name`, `status`, `outcome_status`, `duration_seconds` |

### Querying audit events

```python
from pathlib import Path
from agent_runtime.storage.sqlite import load_telemetry_events

# All events for a specific run
events = load_telemetry_events(Path(".agent_runtime/state.db"), run_id="<run-id>")

# All runner dispatch completions
events = load_telemetry_events(
    Path(".agent_runtime/state.db"),
    event_type="runner.dispatch.completed",
    limit=50,
)
for e in events:
    print(e.created_at, e.payload)
```

---

## Grafana dashboards

The starter dashboard (`observability/grafana/dashboards/workflow_kpis.json`)
contains 8 panels:

1. **Workflow Steps / min** — step rate by action type
2. **Runner Dispatches / min** — dispatch rate by role and outcome
3. **Runner Duration p50 / p95 / p99** — latency percentiles per role
4. **Risk Service Duration p50 / p95** — latency percentiles per outcome status
5. **Risk Service Calls by Status** — pie chart of outcome distribution
6. **Supervisor Heartbeat Age** — stat panel with red threshold at 5 minutes
7. **Drift Findings by Severity** — bar gauge of new findings by severity
8. **Drift Findings by Scanner (last 24 h)** — time-series per scanner and severity

Dashboards are auto-provisioned from
`observability/grafana/provisioning/` — no manual import needed after
`docker compose up`.

---

## Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | OTLP HTTP collector base URL |
| `OTEL_SERVICE_NAME` | _(unused; hardcoded via `configure_telemetry`)_ | — |

Override the endpoint at runtime:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://my-collector:4318 python -m agent_runtime --poll
```

---

## Extending the system

### Adding a new span

```python
from agent_runtime.telemetry import workflow_span

with workflow_span("my_operation", work_item_id=wid, run_id=rid) as span:
    result = do_work()
    if span is not None:
        span.set_attribute("my.result_count", len(result))
```

Or use the decorator:

```python
from agent_runtime.telemetry import traced

@traced("my_operation.execute", component="agent_runtime.my_module", role="coding")
def do_work(execution):
    ...
```

### Adding a new metric

Define the instrument in `agent_runtime/telemetry/metrics.py` following the
lazy-init pattern, then add a recording helper:

```python
_my_counter: Any = None

def _my_instrument() -> Any:
    global _my_counter
    if _my_counter is None:
        meter = _get_meter()
        if meter is not None:
            _my_counter = meter.create_counter("my_events_total", unit="1")
    return _my_counter

def record_my_event(label: str) -> None:
    counter = _my_instrument()
    if counter is not None:
        counter.add(1, {"label": label})
```

Expose `record_my_event` in `agent_runtime/telemetry/__init__.py`.

### Adding a new audit event

```python
from agent_runtime.telemetry import emit_audit_event

emit_audit_event(
    db_path,
    event_type="my_component.something_happened",
    component="agent_runtime.my_component",
    payload={"key": "value", "count": 42},
    run_id=run_id,
    work_item_id=work_item_id,
)
```

---

## Graceful degradation

When the `telemetry` extras are **not** installed:

- `configure_telemetry()` configures only structlog (if available) and stdlib
  logging, returns `False`.
- All span context managers yield `None` (no error).
- All metric recording functions are no-ops.
- `emit_audit_event` still writes to SQLite; it skips the structlog sink if
  structlog is unavailable.
- `get_logger()` returns a stdlib-backed adapter with the same keyword API.

The runtime never fails because telemetry is unavailable.

---

## File inventory

```text
agent_runtime/telemetry/
  __init__.py          public API exports
  _compat.py           graceful degradation shims
  setup.py             OTel SDK + structlog initialisation
  spans.py             span context managers and @traced decorator
  metrics.py           metric instruments and recording helpers
  audit.py             structured audit event emission

agent_runtime/storage/sqlite.py
  telemetry_events     new SQLite table (schema + helpers)
  TelemetryEventRecord dataclass
  append_telemetry_event()
  load_telemetry_events()

observability/
  prometheus/prometheus.yml       Prometheus scrape config
  grafana/provisioning/
    datasources/default.yaml      Jaeger + Prometheus datasources
    dashboards/provider.yaml      Dashboard file provider
  grafana/dashboards/
    workflow_kpis.json            Starter KPI dashboard

docker-compose.observability.yml  Jaeger + Prometheus + Grafana stack
```

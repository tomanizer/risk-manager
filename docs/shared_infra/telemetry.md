# Shared Telemetry Contract

## Purpose

Define one telemetry framework shape that can be reused across `src/` modules
and remain design-aligned with `agent_runtime/telemetry`, without importing
from `agent_runtime`.

## Principles

- independent packages, aligned patterns
- graceful degradation when optional dependencies are absent
- deterministic-service safety first (no payload leakage)
- low-noise, configurable emission with runtime and log-level gates

## Contract requirements

### Logging

- structured records only for governed operation events
- canonical status string in every event
- duration measured via monotonic clock
- explicit `None` for required conditional fields
- status-to-level mapping defined in one place

### Trace context

- include `trace_id` / `span_id` when OpenTelemetry context is valid
- degrade safely when OTel is absent or unconfigured

### Configuration

- enable/disable switch at runtime and env level
- logger-name stability for handler routing (Splunk, ELK, etc.)
- level-based noise control

### Payload discipline

- forbid raw fixtures/snapshots/large arrays in log payloads
- keep low-cardinality fields explicit and stable

## Recommended implementation layout

- `src/shared/telemetry/_compat.py`
- `src/shared/telemetry/setup.py`
- `src/shared/telemetry/logging.py`
- `src/shared/telemetry/spans.py` (optional first)
- `src/shared/telemetry/metrics.py` (optional first)

Module-local helpers (for example in `src/modules/risk_analytics/`) may wrap
shared functions but must not redefine status mapping or payload contracts.

## Review checklist

When a PR touches telemetry:

- no imports from `agent_runtime` into `src/`
- shared contract adherence is explicit
- operation-level tests cover required fields and forbidden-field leakage
- level-gating and disable-gating behavior are tested


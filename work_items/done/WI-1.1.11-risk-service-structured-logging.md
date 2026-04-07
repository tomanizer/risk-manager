# WI-1.1.11

## Linked PRD

PRD-1.1-v2

## Purpose

Add minimum structured logging to the four risk analytics service operations, satisfying the PRD-1.1 "Logging and evidence" section.

Logs are a secondary observability surface only. Typed outputs and replay artifacts remain the canonical evidence surfaces; this slice does not change them.

## Scope

- emit structured operation logs via **`src.shared.telemetry`** (for example `emit_operation`, `node_ref_log_dict`, monotonic timing helpers), per **`docs/shared_infra/telemetry.md`**. Optional dependencies behind that package may include structlog; the service module must not bind its own module-level `structlog.get_logger(__name__)` or duplicate status-to-level rules.
- **must not** import from `agent_runtime` or any module outside `src/` for telemetry
- for this slice, operation emission uses **`include_trace_context=False`** so each record carries only the PRD minimum field set (no `trace_id` / `span_id` in the payload)
- emit one structured log record per operation at the point of return, containing the PRD-required minimum fields:

  | field | applies to |
  |---|---|
  | `operation` | all four operations |
  | `node_ref` | all four operations |
  | `measure_type` | all four operations |
  | `as_of_date` | `get_risk_summary`, `get_risk_delta`, `get_risk_change_profile` |
  | `start_date`, `end_date` | `get_risk_history` |
  | `compare_to_date` | `get_risk_summary`, `get_risk_delta`, `get_risk_change_profile` (always present; `None` when not resolved) |
  | `lookback_window` | `get_risk_summary`, `get_risk_change_profile` |
  | `snapshot_id` | all four (always present; `None` when not provided by caller) |
  | `status` | all four operations |
  | `history_points_used` | `get_risk_summary`, `get_risk_change_profile` (always present; `None` when not returned) |
  | `duration_ms` | all four operations |

- all fields listed above are required in every log record for the operations they apply to; when a listed field is conditional and has no value, it must be logged with `None` rather than omitted
- `duration_ms` is measured from the top of each function to the point of return using `time.monotonic()`; it must be rounded to the nearest millisecond integer
- log level is `INFO` for `OK`, `PARTIAL`, and `MISSING_COMPARE`; `WARNING` for `MISSING_HISTORY`, `DEGRADED`, `MISSING_SNAPSHOT`, `MISSING_NODE`, and `UNSUPPORTED_MEASURE` (mapping centralized in shared telemetry, not reimplemented in `risk_analytics`)
- for `get_risk_summary` and `get_risk_change_profile`, when the operation returns a `ServiceError`, `status` in the log record is the `ServiceError.status_code` string; when it returns a typed object, `status` is the object's `.status.value`
- the log record must not include snapshot contents, raw fixture data, rolling statistics values, or volatility classification values; beyond the required fields above, no additional payload fields are emitted in this slice
- `node_ref` is logged as a concise dict (keys: `node_id`, `node_level`, `hierarchy_scope`, `legal_entity_id`)

## Out of scope

- changes to typed output schemas or any returned object fields
- changes to status derivation logic
- changes to error handling or ServiceError structure
- new typed evidence or trace fields on any output object
- importing from `agent_runtime` or any module outside `src/`
- OpenTelemetry spans or metrics instrumentation in this slice (shared telemetry may support them elsewhere; this WI does not add trace keys to operation payloads)
- replay-suite additions
- `status_reasons` logging (not in PRD minimum set)
- request-id / correlation-id injection (not available at the service layer in v1)
- changes to `get_risk_history` return type (already returns `RiskHistorySeries`, not `ServiceError`)

## Dependencies

- WI-1.1.1-risk-summary-schemas (done)
- WI-1.1.3-risk-summary-history-service (done)
- WI-1.1.4-risk-summary-core-service (done)
- WI-1.1.5-risk-summary-assembly-and-rolling-stats (done)
- WI-1.1.7-risk-change-profile-and-replay (done)
- WI-1.1.10-risk-delta-field-computation (must be done before or alongside; no functional dependency but avoids test-fixture conflicts)

## Target Area

- `src/modules/risk_analytics/service.py` — operation log emission at return (via shared telemetry)
- `src/shared/telemetry/` — shared operation-log contract and helpers (as needed to satisfy this WI; no `agent_runtime` imports)
- `tests/unit/modules/risk_analytics/test_delta_service.py`
- `tests/unit/modules/risk_analytics/test_summary_service.py`
- `tests/unit/modules/risk_analytics/test_change_profile_service.py`
- `tests/unit/modules/risk_analytics/test_history_service.py`
- tests for shared telemetry operation logging where behavior is defined there (if not already covered)

## Acceptance Criteria

- operation logs are emitted through **`src.shared.telemetry`**; **`agent_runtime` is not imported** from `src/` for this behavior
- each of the four operations emits exactly one log record at the point of return
- the log record for each operation contains every required field listed in the Scope section; no required field may be absent
- `duration_ms` is a non-negative integer present on every log record
- `status` in the log record matches the canonical status string of the outcome (typed object status or ServiceError status_code)
- `node_ref` is logged as a dict with keys `node_id`, `node_level`, `hierarchy_scope`, `legal_entity_id`; it is not logged as the raw `NodeRef` repr
- log level is `INFO` for `OK`, `PARTIAL`, `MISSING_COMPARE`; `WARNING` for all degraded and error statuses listed in Scope
- existing unit tests for service **behavior** (typed outputs, statuses, errors) continue to pass; **new** log-capture assertions are added where needed
- new or extended assertions use pytest **`caplog`** against the logger used by shared telemetry operation emission; tests may use **`configure_operation_logging` / `reset_operation_logging_to_defaults`** (or equivalent shared helpers) for isolation; tests **must not** import **`structlog.testing`**
- assertions cover: required fields present; `status` correct for at least one success-like and one error/degraded case per operation; `duration_ms` non-negative integer
- no raw fixture values (snapshot contents, float time-series values, rolling stat floats, volatility enum internals) appear in the log record
- operation log payloads for this service **do not** include `trace_id` or `span_id`

## Suggested Agent

Coding Agent

## Review Focus

- confirm **`agent_runtime` is not imported** into `src/` for logging; shared telemetry stays aligned with `docs/shared_infra/telemetry.md`
- confirm status-to-level mapping is **not** duplicated in `risk_analytics`
- confirm exactly one log record per operation (no double-logging on early-return paths)
- confirm `duration_ms` is measured from function entry, not from after the current-snapshot lookup
- confirm `status` is always a string, never a raw enum object
- confirm `node_ref` is a plain dict, not the `NodeRef` object
- confirm no typed output fields (schema values, rolling stats, volatility flags) appear in the log record
- confirm trace context keys are absent from payloads for these four operations (`include_trace_context=False`)

## Stop Conditions

- stop if any typed output schema is modified
- stop if status derivation or error-handling logic changes
- stop if any import is added from `agent_runtime` into `src/` for this feature
- stop if OpenTelemetry trace keys are added to these operation log payloads in this slice
- stop if more than one log record per operation is emitted
- stop if `status_reasons` or any non-PRD-minimum field is added to log records
- stop if `risk_analytics` reimplements shared telemetry status mapping or payload rules locally

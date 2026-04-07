# WI-1.1.11

## Linked PRD

PRD-1.1-v2

## Purpose

Add minimum structured logging to the four risk analytics service operations, satisfying the PRD-1.1 "Logging and evidence" section.

Logs are a secondary observability surface only. Typed outputs and replay artifacts remain the canonical evidence surfaces; this slice does not change them.

## Scope

- add a module-level `structlog` logger to `src/modules/risk_analytics/service.py`:
  - `_log = structlog.get_logger(__name__)` at module scope
  - import is guarded with a try/except so the module degrades to stdlib `logging` if structlog is unavailable (consistent with the pattern in `agent_runtime/telemetry/_compat.py`)
- emit one structured log record per operation at the point of return, containing the PRD-required minimum fields:

  | field | applies to |
  |---|---|
  | `operation` | all four operations |
  | `node_ref` | all four operations |
  | `measure_type` | all four operations |
  | `as_of_date` | `get_risk_summary`, `get_risk_delta`, `get_risk_change_profile` |
  | `start_date`, `end_date` | `get_risk_history` |
  | `compare_to_date` | `get_risk_summary`, `get_risk_delta`, `get_risk_change_profile` (when relevant) |
  | `lookback_window` | `get_risk_summary`, `get_risk_change_profile` |
  | `snapshot_id` | all four when provided |
  | `status` | all four operations |
  | `history_points_used` | `get_risk_summary`, `get_risk_change_profile` (when returned) |
  | `duration_ms` | all four operations |

- `duration_ms` is measured from the top of each function to the point of return using `time.monotonic()`; it must be rounded to the nearest millisecond integer
- log level is `INFO` for `OK`, `PARTIAL`, and `MISSING_COMPARE`; `WARNING` for `MISSING_HISTORY`, `DEGRADED`, `MISSING_SNAPSHOT`, `MISSING_NODE`, and `UNSUPPORTED_MEASURE`
- for `get_risk_summary` and `get_risk_change_profile`, when the operation returns a `ServiceError`, `status` in the log record is the `ServiceError.status_code` string; when it returns a typed object, `status` is the object's `.status.value`
- the log record must not include snapshot contents, raw fixture data, rolling statistics values, or volatility classification values — only the fields listed above
- `node_ref` is logged as a concise dict (keys: `node_id`, `node_level`, `hierarchy_scope`, `legal_entity_id`)

## Out of scope

- changes to typed output schemas or any returned object fields
- changes to status derivation logic
- changes to error handling or ServiceError structure
- new typed evidence or trace fields on any output object
- importing from `agent_runtime` or any module outside `src/`
- OTel spans or metrics instrumentation (separate telemetry concern)
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

- `src/modules/risk_analytics/service.py` — logger setup and one log call per operation
- `tests/unit/modules/risk_analytics/test_delta_service.py`
- `tests/unit/modules/risk_analytics/test_summary_service.py`
- `tests/unit/modules/risk_analytics/test_change_profile_service.py`
- `tests/unit/modules/risk_analytics/test_history_service.py`

No new modules are created. No other files are touched.

## Acceptance Criteria

- `structlog.get_logger(__name__)` (or stdlib fallback) is initialised at module scope in `service.py`; it must not be imported from `agent_runtime`
- each of the four operations emits exactly one log record at the point of return
- the log record for each operation contains every required field listed in the Scope section; no required field may be absent
- `duration_ms` is a non-negative integer present on every log record
- `status` in the log record matches the canonical status string of the outcome (typed object status or ServiceError status_code)
- `node_ref` is logged as a dict with keys `node_id`, `node_level`, `hierarchy_scope`, `legal_entity_id`; it is not logged as the raw `NodeRef` repr
- log level is `INFO` for `OK`, `PARTIAL`, `MISSING_COMPARE`; `WARNING` for all degraded and error statuses
- the structlog import is guarded with try/except that falls back to stdlib logging; the service must import and function correctly in environments where structlog is absent
- existing unit tests continue to pass without modification
- new log-capture tests added to each of the four test files using `structlog.testing.capture_logs` (or pytest `caplog` for the stdlib fallback path), asserting:
  - required fields are present in the emitted log record
  - `status` value is correct for at least one positive and one error case per operation
  - `duration_ms` is a non-negative integer
- no raw fixture values (snapshot contents, float time-series values, rolling stat floats, volatility enum internals) appear in the log record

## Suggested Agent

Coding Agent

## Review Focus

- confirm `structlog` is not imported from `agent_runtime`; only `structlog` stdlib package or stdlib `logging` fallback
- confirm exactly one log record per operation (no double-logging on early-return paths)
- confirm `duration_ms` is measured from function entry, not from after the current-snapshot lookup
- confirm `status` is always a string, never a raw enum object
- confirm `node_ref` is a plain dict, not the `NodeRef` object
- confirm no typed output fields (schema values, rolling stats, volatility flags) appear in the log record

## Stop Conditions

- stop if any typed output schema is modified
- stop if status derivation or error-handling logic changes
- stop if any import is added from `agent_runtime` or outside `src/`
- stop if OTel spans, metrics, or audit events are added (separate telemetry slice)
- stop if more than one log record per operation is emitted
- stop if `status_reasons` or any non-PRD-minimum field is added to log records

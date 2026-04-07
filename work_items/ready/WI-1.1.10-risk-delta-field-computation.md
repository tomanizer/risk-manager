# WI-1.1.10

## Linked PRD

PRD-1.1-v2

## Purpose

Close the confirmed implementation gap where `delta_abs` and `delta_pct` are hardcoded to `None` across all three as-of-date service operations. The fields are already present in the schemas. PRD-1.1-v2 currently governs the nullability edge case for `delta_pct` when the previous value is zero or `None`, but it does not, in the currently cited material, define the full `delta_pct` formula or the use of `abs(previous_value)`. This WI therefore captures a bounded implementation gap plus a required decision-closure step: the exact computation formula must be confirmed in, or added to, PRD-1.1-v2 before coding.

No schema widening is required or permitted. Once the PRD formula decision is closed, this remains a pure computation correctness fix.

## Scope

- confirm and record in PRD-1.1-v2 the exact delta computation formula to implement for this slice; specifically, confirm whether the intended formula is:
  - `delta_abs = current_value - previous_value` when `previous_value` is not `None`
  - `delta_pct = delta_abs / abs(previous_value)` when `previous_value` is not `None` and `previous_value != 0`
  - both return `None` when `previous_value` is `None`
  - `delta_pct` returns `None` when `previous_value == 0`, `delta_abs` is still computed
- after PRD confirmation/update, introduce a private helper `_compute_delta_fields` in `src/modules/risk_analytics/service.py` to encapsulate the approved rules
- apply `_compute_delta_fields` at the three construction sites that currently hardcode `None`:
  - `get_risk_summary` (lines 289–290)
  - `get_risk_delta` (lines 389–390)
  - `get_risk_change_profile` (lines 783–784)
- extend existing unit test modules to assert correct computed values and correct `None` values across the required case matrix once the PRD-backed formula is approved

## Out of scope

- schema changes to `RiskDelta`, `RiskSummary`, or `RiskChangeProfile`
- changes to status derivation or status precedence logic
- changes to compare-date resolution
- changes to rolling statistics, volatility classification, or history retrieval
- structured logging or observability instrumentation (separate gap)
- replay-suite additions
- new evidence or trace fields
- changes to any module outside `service.py` and the three named unit test files

## Dependencies

- WI-1.1.4-risk-summary-core-service (done)
- WI-1.1.5-risk-summary-assembly-and-rolling-stats (done)
- WI-1.1.7-risk-change-profile-and-replay (done)

## Target Area

- `src/modules/risk_analytics/service.py` — helper introduction and three construction site patches
- `tests/unit/modules/risk_analytics/test_delta_service.py`
- `tests/unit/modules/risk_analytics/test_summary_service.py`
- `tests/unit/modules/risk_analytics/test_change_profile_service.py`

No new test modules are created.

## Acceptance Criteria

- `_compute_delta_fields(current_value, previous_value)` (or equivalent private helper) is introduced and applied identically across all three call sites
- `delta_abs` equals `current_value - previous_value` for all three operations when `previous_value` is not `None`
- `delta_pct` equals `delta_abs / abs(previous_value)` when `previous_value` is not `None` and `previous_value != 0`
- `delta_pct` is `None` and `delta_abs` is computed (non-`None`) when `previous_value == 0.0` (Business Rule 3)
- both `delta_abs` and `delta_pct` are `None` when `previous_value` is `None` (MISSING_COMPARE case)
- DEGRADED status does not suppress delta computation when both values are resolved — deltas are computed whenever `previous_value` is available, regardless of status
- no field on `RiskDelta`, `RiskSummary`, or `RiskChangeProfile` is added, removed, or renamed
- the helper is private (prefixed `_`) and not exported from the package
- new explicit test cases added to each of the three test files asserting:
  - normal case: both fields computed and non-`None`
  - zero-prior case: `delta_abs` computed, `delta_pct` is `None`
  - null-prior / MISSING_COMPARE case: both fields are `None`

## Suggested Agent

Coding Agent

## Review Focus

- `abs(previous_value)` used in denominator (not `previous_value`), to handle negative prior values correctly
- consistent application across all three construction sites — no site left behind
- zero-prior case: `delta_abs` must not be suppressed, only `delta_pct`
- DEGRADED-with-prior case: computation must proceed, status does not gate delta computation
- no status-logic changes introduced as a side effect
- no schema changes of any kind

## Stop Conditions

- stop if the implementation requires adding, removing, or renaming any field on `RiskDelta`, `RiskSummary`, or `RiskChangeProfile`
- stop if status derivation logic in any of the three operations is modified
- stop if rolling statistics, volatility classification, compare-date resolution, or history retrieval code is touched
- stop if structured logging, observability, or replay-suite work enters the PR
- stop if `_compute_delta_fields` is exported from the package public surface
- stop if the helper is not shared across all three construction sites

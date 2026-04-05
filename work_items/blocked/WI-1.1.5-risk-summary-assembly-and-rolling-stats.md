# WI-1.1.5

## Linked PRD

PRD-1.1-v2

## Purpose

Implement `get_risk_summary` by composing first-order retrieval with rolling-stat history inputs.

## Scope

- `get_risk_summary`
- reuse of shared current/prior retrieval logic from WI-1.1.4
- rolling mean
- rolling std
- rolling min/max
- `history_points_used`
- summary-status derivation for insufficient or degraded history
- package export for `get_risk_summary`

## Out of scope

- `get_risk_delta`
- `RiskChangeProfile`
- `volatility_regime`
- `volatility_change_flag`
- replay-suite coverage
- new evidence/trace fields

## Dependencies

- WI-1.1.1-risk-summary-schemas
- WI-1.1.2-risk-summary-fixtures
- WI-1.1.3-risk-summary-history-service
- WI-1.1.4-risk-summary-core-service
- WI-1.1.6-risk-summary-business-day-resolver
- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Target Area

- `src/modules/risk_analytics/service.py`
- `src/modules/risk_analytics/__init__.py`
- `tests/unit/modules/risk_analytics/`

Create the summary-service unit test module in the existing risk-analytics unit-test package as part of this slice.

## Acceptance Criteria

- `get_risk_summary` reuses WI-1.1.4 first-order retrieval semantics without divergence in compare-date handling, delta construction, or status precedence
- rolling statistics use only valid history points within the resolved lookback window
- `rolling_mean`, `rolling_min`, and `rolling_max` require at least 1 valid history point
- `rolling_std` uses sample standard deviation (`ddof = 1`) and is null when fewer than 2 valid history points are available
- `history_points_used` equals the number of valid history points used for rolling-stat calculation
- when current value exists but history is insufficient, the service still returns the summary object and uses `MISSING_HISTORY` exactly as defined in PRD-1.1-v2
- degraded history inputs upgrade the summary status according to PRD-1.1-v2 precedence
- top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` mirror `node_ref` exactly
- this slice introduces no `RiskChangeProfile`, no volatility logic, no replay-suite tests, and no new evidence/trace fields
- unit tests cover complete-history, sparse-history, degraded-history, one-point versus two-point rolling windows, and `history_points_used`

## Blocking Reason

- PRD-1.1-v2 says omitted `lookback_window` must use a service default, but current `main` does not define that default anywhere in merged canon
- coding must not invent the omitted-`lookback_window` behavior or default value

## Suggested Agent

Issue Planner or PRD Author for blocker closure, then Coding Agent

## Review Focus

- summary contract fidelity
- rolling-stat correctness
- status correctness for insufficient and degraded history
- confirmation that `lookback_window` default semantics are explicit before promotion back to `ready/`

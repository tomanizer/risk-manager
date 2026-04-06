# WI-1.1.4

## Linked PRD

PRD-1.1-v2

## Purpose

Implement `get_risk_delta` and the shared first-order retrieval logic it requires.

## Scope

- `get_risk_delta`
- shared current/prior retrieval helper logic inside the service module
- compare-date defaulting through the canonical business-day resolver
- explicit compare-date validation and handling
- first-order status derivation needed for delta retrieval
- direct population of top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` from `node_ref`
- package export for `get_risk_delta`

## Out of scope

- `get_risk_summary`
- rolling statistics
- `history_points_used`
- `RiskChangeProfile`
- volatility flags or volatility-regime logic
- replay-suite coverage
- new evidence/trace fields
- service-layer refactors outside the named files

## Dependencies

- WI-1.1.1-risk-summary-schemas
- WI-1.1.2-risk-summary-fixtures
- WI-1.1.6-risk-summary-business-day-resolver
- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Target Area

- `src/modules/risk_analytics/service.py`
- `src/modules/risk_analytics/__init__.py`
- `tests/unit/modules/risk_analytics/`

Create the delta-service unit test module in the existing risk-analytics unit-test package as part of this slice.

## Acceptance Criteria

- `get_risk_delta` returns a typed `RiskDelta` for a supported scoped node, measure, and `as_of_date`
- current value is read from the pinned `as_of_date` snapshot row for the exact scoped `node_ref`
- omitted `compare_to_date` defaults through the canonical business-day resolver from WI-1.1.6
- explicit `compare_to_date` is honored exactly and validated through the same canonical calendar path
- invalid explicit compare dates must fail through canonical resolver validation rather than silently falling back
- if the current snapshot for `as_of_date` is missing, the result status is `MISSING_SNAPSHOT`
- if the current snapshot exists but the scoped node/measure does not, the result status is `MISSING_NODE`
- if the compare snapshot or compare row is missing while the current row exists, current values are returned, prior and delta fields are null, and the result status is `MISSING_COMPARE`
- if the current snapshot or current row is degraded, the result status is `DEGRADED` and lower-precedence compare issues do not overwrite it
- `delta_pct` is null when `previous_value` is null or zero
- top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` mirror `node_ref` exactly
- reachable statuses in this slice are explicit and limited to `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`, `DEGRADED`, `MISSING_COMPARE`, and `OK`; `PARTIAL` and `MISSING_HISTORY` remain deferred because no history or rolling-stat behavior is in scope
- this slice introduces no `get_risk_summary` surface, no replay-suite tests, and no new evidence/trace fields beyond the approved replay/version metadata already present on the contract
- unit tests cover compare-date defaulting, explicit compare handling, missing compare behavior, zero-prior handling, degraded-status precedence, scope fidelity, and mirrored top-level fields

## Suggested Agent

Coding Agent

## Review Focus

- first-order delta correctness
- compare-date semantics
- status-precedence correctness for the statuses reachable in this slice
- scope fidelity and mirror-field fidelity
- strict out-of-scope discipline

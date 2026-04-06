# WI-1.1.4

## Linked PRD

PRD-1.1-v2

## Purpose

Implement `get_risk_delta` as a first-order retrieval surface that returns a `RiskDelta` only when a current point exists.

Current-point failures must not fabricate partial `RiskDelta` objects. In this slice, those outcomes are returned as typed service errors rather than as partially populated `RiskDelta` responses.

## Scope

- `get_risk_delta`
- shared current/prior retrieval helper logic inside the service module
- compare-date defaulting through the canonical business-day resolver
- explicit compare-date validation and handling
- first-order status derivation for object-returning delta retrieval
- typed service-error routing for current-point failures that cannot be represented honestly by the current `RiskDelta` contract
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
- widening the `RiskDelta` schema
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

## Outcome Model

`get_risk_delta` returns a `RiskDelta` only when all fields required by the current contract can be populated honestly, including:

- `current_value`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

### Returned as `RiskDelta` statuses

These outcomes remain in-object statuses because a valid current point exists and a `RiskDelta` can be constructed without fabrication:

- `OK`
- `DEGRADED`
- `MISSING_COMPARE`

### Returned as typed service errors

These outcomes are not returned as partial `RiskDelta` objects in this slice:

- `UNSUPPORTED_MEASURE`
- `MISSING_SNAPSHOT`
- `MISSING_NODE`

### Returned as typed validation errors

These outcomes remain request-validation failures rather than `RiskDelta` responses:

- invalid explicit `compare_to_date`
- invalid or blank `snapshot_id`
- any request that fails existing typed contract or business-day validation

## Acceptance Criteria

- `get_risk_delta` returns a typed `RiskDelta` only when a current scoped point exists for the requested `as_of_date`
- current value is read from the pinned `as_of_date` snapshot row for the exact scoped `node_ref`
- omitted `compare_to_date` defaults through the canonical business-day resolver from WI-1.1.6
- explicit `compare_to_date` is honored exactly and validated through the same canonical calendar path
- invalid explicit compare dates fail through validation rather than silently falling back
- if the compare snapshot or compare row is missing while the current row exists, current values are returned, prior and delta fields are null, and the result status is `MISSING_COMPARE`
- if the current snapshot and current row exist but either is degraded, the returned `RiskDelta.status` is `DEGRADED` and lower-precedence compare issues do not overwrite it
- `delta_pct` is null when `previous_value` is null or zero
- top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` mirror `node_ref` exactly
- `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, and `MISSING_NODE` are surfaced as typed service errors in this slice, not as partially populated `RiskDelta` objects
- reachable in-object delta statuses in this slice are limited to `OK`, `DEGRADED`, and `MISSING_COMPARE`
- this slice introduces no `get_risk_summary` surface, no replay-suite tests, no new evidence/trace fields beyond the approved replay/version metadata already present on the contract, and no schema widening
- unit tests cover compare-date defaulting, explicit compare handling, missing compare behavior, zero-prior handling, degraded-status precedence, scope fidelity, mirrored top-level fields, and the object-vs-service-error boundary for current-point failures

## Suggested Agent

Coding Agent

## Review Focus

- first-order delta correctness
- compare-date semantics
- contract fidelity between object-returning and error-returning paths
- scope fidelity and mirror-field fidelity
- strict out-of-scope discipline

## Stop Conditions

- stop if implementation would need to fabricate `current_value`, `snapshot_id`, or replay/version metadata for a missing current point
- stop if implementation would need to widen the `RiskDelta` schema
- stop if implementation would need to return `get_risk_summary`
- stop if rolling statistics, `history_points_used`, `RiskChangeProfile`, volatility logic, or replay work enters the PR
- stop if a required current-point-failure error contract is not already expressible through the repository's existing typed service-error path

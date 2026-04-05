# WI-1.1.3

## Linked PRD

PRD-1.1-v2

## Purpose

Implement history retrieval for a node and measure.

## Scope

- `get_risk_history`
- date-range validation
- ascending ordering
- typed status handling
- exact scope-aware node resolution
- snapshot-pinned retrieval

## Out of scope

- summary logic
- rolling statistics
- delta logic

## Dependencies

- WI-1.1.1
- WI-1.1.2
- WI-1.1.6
- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Target Area

- `src/modules/risk_analytics/service.py`
- `src/modules/risk_analytics/__init__.py`
- `tests/unit/modules/risk_analytics/`

## Acceptance Criteria

- `get_risk_history` uses explicit `start_date` and `end_date` inputs with inclusive range semantics
- invalid date ranges fail explicitly and do not fabricate a `RiskHistorySeries`
- if `snapshot_id` is provided, it is treated as the history-request anchor snapshot and must resolve to `end_date`
- returned history points are ordered ascending by date and remain within the inclusive requested range
- unsupported measure handling is explicit and returns `UNSUPPORTED_MEASURE` when surfaced as a service response
- missing snapshot returns `MISSING_SNAPSHOT`
- missing node returns `MISSING_NODE`
- zero valid points in range returns `MISSING_HISTORY`
- sparse valid points in range return `PARTIAL`
- degraded snapshot rows return `DEGRADED`
- `require_complete=true` upgrades otherwise partial history results to `DEGRADED`
- node resolution is exact within scope
- unit tests cover status behavior and snapshot-anchor semantics
- dedicated replay-suite coverage is deferred to WI-1.1.5

## Suggested Agent

Coding Agent

## Review Focus

- history-status correctness
- snapshot-anchor semantics
- scope fidelity
- ordering and range correctness
- no hidden aggregation logic
- no replay-scope creep beyond WI-1.1.3

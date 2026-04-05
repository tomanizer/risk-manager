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

- `src/modules/risk_analytics/`
- `tests/unit/modules/risk_analytics/`

## Acceptance Criteria

- returns correct ordered history
- invalid date ranges handled explicitly
- missing node and missing data handled explicitly
- node resolution is exact within scope
- unit tests included

## Suggested Agent

Coding Agent

## Review Focus

- correctness
- degraded handling
- scope fidelity
- no hidden aggregation logic

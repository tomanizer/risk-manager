# WI-1.1.3

## Linked PRD

PRD-1.1

## Purpose

Implement history retrieval for a node and measure.

## Scope

- `get_risk_history`
- date-range validation
- ascending ordering
- typed status handling

## Out of scope

- summary logic
- rolling statistics
- delta logic

## Acceptance Criteria

- returns correct ordered history
- invalid date ranges handled explicitly
- missing node and missing data handled explicitly
- unit tests included

## Suggested Agent

Coding Agent

## Review Focus

- correctness
- degraded handling
- no hidden aggregation logic

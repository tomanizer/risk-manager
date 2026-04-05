# WI-1.1.4

## Linked PRD

PRD-1.1-v2

## Purpose

Implement `get_risk_summary`, `get_risk_delta`, and the first-order status logic they require.

## Scope

- current value retrieval
- compare-to logic
- delta computation
- status derivation
- `RiskDelta` implementation as a distinct first-order object
- scope-aware retrieval behavior

## Out of scope

- factor decomposition
- `RiskChangeProfile`
- narratives
- agent usage

## Dependencies

- WI-1.1.1
- WI-1.1.2
- WI-1.1.3
- WI-1.1.6
- ADR-001
- ADR-002
- ADR-004

## Target Area

- `src/modules/risk_analytics/`
- `tests/unit/modules/risk_analytics/`
- `tests/replay/`

## Acceptance Criteria

- correct current/prior/delta behavior
- `delta_pct` null when prior is zero or null
- explicit missing compare handling
- status precedence follows PRD-1.1-v2
- no collapse of `RiskDelta` into `RiskSummary`
- tests included

## Suggested Agent

Coding Agent

## Review Focus

- delta correctness
- status correctness
- scope semantics
- strict PRD adherence

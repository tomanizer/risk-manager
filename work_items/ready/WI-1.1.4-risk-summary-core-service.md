# WI-1.1.4

## Linked PRD

PRD-1.1

## Purpose

Implement `get_risk_summary` and `get_risk_delta`.

## Scope

- current value retrieval
- compare-to logic
- delta computation
- status derivation
- reuse or define `RiskDelta`

## Out of scope

- factor decomposition
- narratives
- agent usage

## Acceptance Criteria

- correct current/prior/delta behavior
- `delta_pct` null when prior is zero or null
- explicit missing compare handling
- tests included

## Suggested Agent

Coding Agent

## Review Focus

- delta correctness
- status correctness
- strict PRD adherence

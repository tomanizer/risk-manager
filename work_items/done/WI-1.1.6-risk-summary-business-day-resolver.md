# WI-1.1.6

## Linked PRD

PRD-1.1-v2

## Purpose

Implement the canonical business-day resolver for compare-to defaults and replay consistency.

## Scope

- prior business-day resolution
- pinned fixture calendar support
- pinned snapshot calendar support
- deterministic behavior across replay

## Out of scope

- holiday service integration beyond the canonical configured source
- narrative handling

## Dependencies

- WI-1.1.1-risk-summary-schemas
- WI-1.1.2-risk-summary-fixtures
- ADR-002
- ADR-004

## Target Area

- `src/modules/risk_analytics/time/`
- `tests/unit/modules/risk_analytics/`

## Acceptance Criteria

- prior business day is deterministic and scope-independent
- replay runs use pinned calendar metadata
- no consumer-side date inference is required

## Suggested Agent

Coding Agent

## Review Focus

- determinism
- replay consistency
- simplicity

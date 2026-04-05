# WI-1.1.5

## Linked PRD

PRD-1.1-v2

## Purpose

Add rolling statistics and replay tests for the Risk Summary Service.

## Scope

- rolling mean
- rolling std
- rolling min/max
- history points used
- `RiskChangeProfile`
- `volatility_regime`
- `volatility_change_flag`
- replay tests pinned by snapshot

## Out of scope

- new measures
- UI
- orchestrators

## Dependencies

- WI-1.1.1-risk-summary-schemas
- WI-1.1.2-risk-summary-fixtures
- WI-1.1.3-risk-summary-history-service
- WI-1.1.4-risk-summary-core-service
- WI-1.1.6-risk-summary-business-day-resolver
- ADR-001
- ADR-002
- ADR-003

## Target Area

- `src/modules/risk_analytics/`
- `tests/unit/modules/risk_analytics/`

This slice is expected to add replay coverage. Create the replay test directory in-slice when adding those tests rather than treating it as an already-existing target area.

## Acceptance Criteria

- rolling stats use only available valid points
- `rolling_std` uses sample standard deviation
- volatility flags are deterministic and explicit
- replay tests stable across repeated runs
- degraded history handled explicitly
- `RiskChangeProfile` retains top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` fields that exactly mirror `node_ref` and therefore match `RiskSummary`
- replay tests pin the approved replay/version metadata only; explicit evidence/trace fields remain deferred until the shared contract exists

## Suggested Agent

Coding Agent

## Review Focus

- statistical correctness
- replayability
- volatility semantics
- no hidden time dependence

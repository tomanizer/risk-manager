# WI-1.1.2

## Linked PRD

PRD-1.1-v2

## Purpose

Create a deterministic synthetic fixture pack for risk summary testing and replay.

## Scope

- synthetic hierarchy
- 5+ business dates
- `TOP_OF_HOUSE` scope
- at least 2 `LEGAL_ENTITY` scopes
- VaR and ES values
- missing compare case
- zero prior case
- partial snapshot case
- modest delta with elevated volatility
- large delta with stable volatility
- fixture loader

## Out of scope

- service logic
- orchestrators
- UI

## Dependencies

- WI-1.1.1
- docs/implementation/PRD-1.1-foundation-slice.md
- ADR-002
- ADR-004

## Target Area

- `fixtures/risk_analytics/`
- `src/modules/risk_analytics/fixtures/`
- `tests/unit/modules/risk_analytics/`

## Acceptance Criteria

- fixtures are deterministic
- loader is simple and documented
- fixtures support positive, edge, and degraded cases
- fixture calendar is pinned for replay-safe business-day resolution

## Suggested Agent

Coding Agent

## Review Focus

- determinism
- coverage of degraded scenarios
- scope coverage
- simplicity

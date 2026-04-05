# WI-1.1.1

## Linked PRD

PRD-1.1-v2

## Purpose

Define the core enums and typed schemas for the Risk Summary Service.

## Scope

- `MeasureType`
- `HierarchyScope`
- `SummaryStatus`
- `NodeLevel`
- `VolatilityRegime`
- `VolatilityChangeFlag`
- `NodeRef`
- `RiskDelta`
- `RiskSummary`
- `RiskChangeProfile`
- `RiskHistoryPoint`
- `RiskHistorySeries`

## Out of scope

- service logic
- fixture loading
- rolling statistics
- history retrieval

## Dependencies

- docs/implementation/PRD-1.1-foundation-slice.md
- ADR-001
- ADR-002
- ADR-004

## Target Area

- `src/modules/risk_analytics/contracts/`
- `tests/unit/modules/risk_analytics/`

## Acceptance Criteria

- schemas are explicit and typed
- nullability is defined
- enums and structures match PRD-1.1-v2
- `NodeRef` scope validation is explicit
- `RiskDelta` remains first-order only
- `RiskChangeProfile` remains distinct from `RiskDelta`
- unit tests validate schema behavior

## Suggested Agent

Coding Agent

## Review Focus

- contract fidelity
- schema completeness
- scope semantics
- future extensibility without overengineering

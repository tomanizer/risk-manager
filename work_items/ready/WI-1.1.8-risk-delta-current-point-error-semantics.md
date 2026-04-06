# WI-1.1.8

## Linked PRD

PRD-1.1-v2

## Purpose

Clarify current-point-failure outcome semantics for as-of-date retrieval operations so coding does not invent whether failures are returned as typed objects or typed service errors.

## Scope

- clarify in PRD-1.1-v2 that `get_risk_delta` returns a `RiskDelta` only when a current point exists
- clarify whether the same object-vs-error rule also applies to `get_risk_summary` and `get_risk_change_profile`, whose contracts also require current-value and replay/version fields
- state explicitly which canonical outcomes are object statuses versus typed service errors for as-of-date retrieval
- align the degraded/error-cases section with the API-surface section
- align the status-model wording so it does not imply that every listed status must always be representable inside every output object

## Out of scope

- contract-schema changes
- service implementation
- replay-suite work
- volatility-policy changes

## Dependencies

- PRD-1.1-v2
- ADR-001
- ADR-002

## Target Area

- `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`

## Acceptance Criteria

- PRD explicitly distinguishes object-returning outcomes from typed service-error outcomes for `get_risk_delta`
- PRD states whether `MISSING_SNAPSHOT`, `MISSING_NODE`, and `UNSUPPORTED_MEASURE` are object statuses, service errors, or operation-specific outcomes
- PRD no longer requires fabricated fields for current-point-missing paths
- PRD language is consistent across API surface, output contracts, status model, and degraded/error cases

## Suggested Agent

PRD Author

## Review Focus

- request and status semantics
- consistency across PRD sections
- no ambiguity pushed to coding

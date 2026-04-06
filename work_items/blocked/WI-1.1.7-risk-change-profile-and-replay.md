# WI-1.1.7

## Linked PRD

PRD-1.1-v2

## Purpose

Implement `get_risk_change_profile` and replay-suite coverage once volatility canon is explicit.

## Scope

- `get_risk_change_profile`
- `volatility_regime`
- `volatility_change_flag`
- replay-suite coverage for completed as-of-date retrieval surfaces
- deterministic replay assertions for pinned snapshot and version metadata

## Out of scope

- new measures
- new evidence/trace fields
- UI or orchestrator work
- service-layer refactors outside the named files and replay test area

## Dependencies

- WI-1.1.1-risk-summary-schemas
- WI-1.1.2-risk-summary-fixtures
- WI-1.1.3-risk-summary-history-service
- WI-1.1.4-risk-summary-core-service
- WI-1.1.5-risk-summary-assembly-and-rolling-stats
- WI-1.1.6-risk-summary-business-day-resolver
- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Target Area

- `src/modules/risk_analytics/service.py`
- `src/modules/risk_analytics/__init__.py`
- `tests/unit/modules/risk_analytics/`

Create the change-profile unit test module in the existing risk-analytics unit-test package as part of this slice.

- `tests/`

Create the replay test package and risk-analytics replay test module in-slice rather than treating them as pre-existing paths.

## Acceptance Criteria

- `get_risk_change_profile` extends the completed summary surface without diverging from WI-1.1.4 and WI-1.1.5 first-order or rolling-stat semantics
- `volatility_regime` is derived from explicit, versioned threshold rules
- `volatility_change_flag` is derived from explicit short-window versus baseline-window dispersion rules
- replay tests pin the fully resolved request context required by PRD-1.1-v2, including resolved compare date and lookback window when relevant
- replay tests prove stable outputs for repeated runs against the same pinned snapshot context
- this slice introduces no new evidence/trace fields beyond the approved replay/version metadata already present on the contracts

## Blocking Reason

- PRD-1.1-v2 requires versioned threshold rules for `volatility_regime`, but current `main` does not define the threshold values or where they are configured
- PRD-1.1-v2 requires `volatility_change_flag` to compare short-window and baseline-window dispersion measures, but current `main` does not define those window lengths or the deterministic rule for `RISING` versus `FALLING`
- coding must not invent volatility thresholds, baseline windows, or replay assertions for semantics that remain open

## Suggested Agent

Risk Methodology Spec Agent or PRD Author for blocker closure, then Coding Agent

## Review Focus

- volatility-methodology fidelity
- replay determinism
- no hidden policy invention in thresholds or windowing

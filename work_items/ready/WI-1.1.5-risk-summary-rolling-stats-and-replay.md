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
- `get_risk_summary` and `get_risk_change_profile` use a default `lookback_window` of 60 business days anchored on `as_of_date` and inclusive of `as_of_date`
- `get_risk_delta` does not accept or use `lookback_window`
- `RiskChangeProfile.volatility_regime` uses the canonical normalized `volatility_ratio` policy with bands:
  - `LOW` when `< 0.05`
  - `NORMAL` when `>= 0.05` and `< 0.15`
  - `ELEVATED` when `>= 0.15` and `< 0.30`
  - `HIGH` when `>= 0.30`
- `RiskChangeProfile.volatility_change_flag` uses the canonical short-window versus baseline-window dispersion policy with:
  - `short_window = 10` business days
  - `baseline_window = 60` business days
  - `FALLING` when `short_std / baseline_std <= 0.80`
  - `STABLE` when `0.80 < short_std / baseline_std < 1.20`
  - `RISING` when `short_std / baseline_std >= 1.20`
- `volatility_regime` returns `INSUFFICIENT_HISTORY` when fewer than 20 valid baseline-window points are available
- `volatility_change_flag` returns `INSUFFICIENT_HISTORY` when fewer than 5 valid short-window points or fewer than 20 valid baseline-window points are available
- degraded or invalid history rows are excluded from volatility calculations, and if exclusions drop valid counts below the minimums the affected volatility output becomes `INSUFFICIENT_HISTORY`
- volatility flags are deterministic and explicit
- replay tests stable across repeated runs
- degraded history handled explicitly
- `RiskChangeProfile` retains top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` fields that exactly mirror `node_ref` and therefore match `RiskSummary`
- replay tests pin the approved replay/version metadata only; explicit evidence/trace fields remain deferred until the shared contract exists
- replay tests pin the effective volatility-policy ruleset and window policy explicitly, including `VOLATILITY_RULES_V1`, `baseline_window = 60`, `short_window = 10`, business-day basis, and inclusive anchoring on `as_of_date`

## Suggested Agent

Coding Agent

## Review Focus

- statistical correctness
- replayability
- volatility semantics
- no hidden time dependence

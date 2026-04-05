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

- WI-1.1.1
- WI-1.1.2
- WI-1.1.3
- WI-1.1.4
- WI-1.1.6
- ADR-001
- ADR-002
- ADR-003

## Target Area

- `src/modules/risk_analytics/`
- `tests/unit/modules/risk_analytics/`
- `tests/replay/`

## Acceptance Criteria

- rolling stats use only available valid points
- `rolling_std` uses sample standard deviation
- volatility flags are deterministic and explicit
- replay tests stable across repeated runs
- degraded history handled explicitly

## Suggested Agent

Coding Agent

## Review Focus

- statistical correctness
- replayability
- volatility semantics
- no hidden time dependence

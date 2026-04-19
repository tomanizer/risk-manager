# PRD-4.3: Time Series Walker

## Variant
Walker PRD (interpretive over `RiskChangeProfile`)

## Purpose
Classify trend, outlier, regime-change, and volatility-direction signals from typed upstream risk-change output; emit structured caveat codes and confidence without recomputing deterministic service fields.

## In scope
- single upstream call to `get_risk_change_profile`
- typed `TimeSeriesAssessment` wrapper and closed enum vocabularies
- deterministic rule tables over `RiskChangeProfile` fields
- telemetry via shared `emit_operation` contract

## Out of scope
- raw history series exposure (`get_risk_history`) in v1
- Data Controller trust gate inside the walker
- narrative prose and recommended-next-step fields

## Core output
`TimeSeriesAssessment` (see normative PRD `docs/prds/phase-2/PRD-4.3-time-series-walker-v1.md`).

## Acceptance criteria
- parity with upstream `ServiceError` and validation errors
- replay determinism for equal upstream inputs
- no imports outside public `risk_analytics` and shared telemetry surfaces

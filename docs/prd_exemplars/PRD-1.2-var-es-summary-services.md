# PRD-1.2: VaR and ES Summary Services

## Variant
Deterministic Service PRD

## Purpose
Provide canonical deterministic retrieval of current and comparison-period VaR and ES summaries for supported hierarchy nodes.

## In scope
- current VaR summary retrieval
- current ES summary retrieval
- optional compare-to date
- default compare-to previous business day
- summary metadata including snapshot and service version

## Out of scope
- contributor breakdowns
- histories beyond current/prior comparison
- UI rendering
- governance narrative

## Core output
`RiskSummary`
- node
- metric
- as_of
- compare_to
- current_value
- previous_value
- delta_abs
- delta_pct
- rolling_std_60d
- summary_status
- snapshot_id
- methodology_version
- service_version

## Core rules
1. Missing current snapshot is blocking.
2. Missing compare snapshot returns partial output with explicit status.
3. delta_pct and delta_abs are null when previous value is missing; delta_pct is also null when previous value is zero.
4. Service is read-only and replayable.

## Acceptance criteria
- returns valid RiskSummary for supported node/date
- returns typed partial output for missing compare date
- returns typed errors for invalid node or unsupported metric
- includes metadata fields and replay support

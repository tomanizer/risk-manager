# PRD-1.1: Risk Summary Service

## Header

- **PRD ID:** PRD-1.1
- **Title:** Risk Summary Service
- **Phase:** Phase 1
- **Status:** Draft
- **Module:** Risk Analytics
- **Type:** Deterministic service
- **Primary owner:** Technical Owner, Risk Analytics
- **Business owner:** Market Risk Reporting Owner
- **Control owner:** Risk Data / Controls Owner

## Purpose

Provide the canonical deterministic service for retrieving daily VaR and Expected Shortfall summaries across the risk hierarchy.

This is the first foundational service for the platform. It must be simple, replayable, typed, and safe to consume by later walkers, orchestrators, dashboards, and governance processes.

## Why this exists

Today, many downstream processes need the same core question answered:

- what is the current VaR or ES for a node?
- what changed versus the comparison date?
- what is the recent history?
- is the answer complete, partial, or degraded?

This service gives one governed answer instead of many inconsistent ones.

## In scope

- Retrieve daily VaR and ES summary for a target node
- Support hierarchy levels:
  - firm
  - division
  - area
  - desk
  - book
  - position
  - trade
- Support comparison to prior business day or explicit comparison date
- Return:
  - current value
  - prior value
  - absolute delta
  - percentage delta
  - basic rolling statistics
  - data status / completeness flags
- Support history retrieval over a date range
- Use typed schemas only
- Use deterministic fixtures and replay-friendly interfaces
- Preserve snapshot metadata and service version metadata

## Out of scope

- Risk-factor decomposition
- Contributor ranking
- Greek explain
- PnL vectors
- limit checks
- FRTB PLA / HPL / RTPL logic
- narrative generation
- agent reasoning
- UI rendering
- approvals or workflow orchestration

## Consumers

Primary consumers:

- Quant Walker
- Time Series Walker
- Governance / Reporting Walker
- Capital & Desk Status module
- Daily Risk Investigation orchestrator

Secondary consumers:

- analyst review UI
- dashboards
- replay harness
- test fixtures

## Core principles

- deterministic core, no LLM logic
- one canonical answer per request
- explicit degraded states
- replayable by snapshot and date
- typed contracts only
- no hidden business logic in consumers

## Canonical concepts

### Supported measures

- `VAR_1D_99`
- `VAR_10D_99`
- `ES_97_5`

### Supported node reference

A target must be expressed as a typed hierarchy address, not a free-text string.

### Supported currencies

- base reporting currency only in v1
- optional currency parameter allowed only if already available in canonical store
- no ad hoc FX conversion logic in this service

## Inputs

### Required inputs

- `node_ref`
- `as_of_date`
- `measure_type`

### Optional inputs

- `compare_to_date`
- `lookback_window`
- `require_complete`
- `snapshot_id`

### Input rules

- if `compare_to_date` is omitted, default to prior business day
- if `lookback_window` is omitted, use service default for rolling stats
- if `require_complete=true`, partial results must return an explicit degraded error/status
- if `snapshot_id` is provided, retrieval must be pinned to that snapshot

## Outputs

### Primary output: `RiskSummary`

Fields:

- `node_ref`
- `node_level`
- `measure_type`
- `as_of_date`
- `compare_to_date`
- `current_value`
- `previous_value`
- `delta_abs`
- `delta_pct`
- `rolling_mean`
- `rolling_std`
- `rolling_min`
- `rolling_max`
- `history_points_used`
- `status`
- `status_reasons`
- `is_partial`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

### Secondary output: `RiskHistoryPoint`

Fields:

- `node_ref`
- `measure_type`
- `date`
- `value`
- `snapshot_id`
- `status`

### Secondary output: `RiskHistorySeries`

Fields:

- `node_ref`
- `measure_type`
- `start_date`
- `end_date`
- `points`
- `status`
- `status_reasons`
- `service_version`

## Status model

Allowed summary statuses:

- `OK`
- `PARTIAL`
- `MISSING_COMPARE`
- `MISSING_HISTORY`
- `MISSING_NODE`
- `MISSING_SNAPSHOT`
- `UNSUPPORTED_MEASURE`
- `DEGRADED`

Rules:

- status must always be explicit
- `PARTIAL` is valid only when current value exists but some comparison/history component is missing
- status reasons must be machine-readable strings, not only prose

## API surface

### `get_risk_summary`

Purpose:
Return current summary plus comparison and rolling stats.

Inputs:

- `node_ref`
- `as_of_date`
- `measure_type`
- `compare_to_date=None`
- `lookback_window=60`
- `require_complete=False`
- `snapshot_id=None`

Returns:

- `RiskSummary`

### `get_risk_history`

Purpose:
Return dated history for a node and measure.

Inputs:

- `node_ref`
- `measure_type`
- `start_date`
- `end_date`
- `snapshot_id=None`

Returns:

- `RiskHistorySeries`

### `get_risk_delta`

Purpose:
Return a minimal delta-focused object for fast consumers.

Inputs:

- `node_ref`
- `as_of_date`
- `measure_type`
- `compare_to_date=None`
- `snapshot_id=None`

Returns:

- thin typed object or reuse `RiskSummary`

## Business rules

1. Current value is mandatory for a valid summary.
2. Comparison is optional unless explicitly required.
3. Percentage delta must be null when previous value is zero or null.
4. Rolling statistics must use only available valid points.
5. History must be ordered ascending by date.
6. Hierarchy references must be exact and typed.
7. This service does not aggregate from raw trades on demand in v1 unless already present in canonical store.
8. No narrative text in outputs.

## Degraded and error cases

### Case: current point missing

Result:

- `status = MISSING_SNAPSHOT` or `MISSING_NODE`
- no fabricated values

### Case: compare point missing

Result:

- current value returned
- prior and deltas null
- `status = PARTIAL` or `MISSING_COMPARE`

### Case: insufficient history

Result:

- current summary still returned if available
- rolling fields calculated from available points or null if too few
- `status = MISSING_HISTORY` or `PARTIAL`

### Case: unsupported measure

Result:

- typed validation failure or `UNSUPPORTED_MEASURE`

### Case: partial snapshot

Result:

- explicit `DEGRADED` or `PARTIAL`
- include reason codes

## Replay requirements

- service must support replay by `snapshot_id`
- same input plus same snapshot must yield same output
- fixtures must pin expected outputs
- no dependency on current system clock beyond `generated_at`

## Logging and evidence

Minimum structured logging:

- request id
- node_ref
- measure_type
- as_of_date
- compare_to_date
- snapshot_id
- returned status
- number of history points used
- duration

## Acceptance criteria

### Functional

- returns valid VaR summary for supported node/date
- returns valid ES summary for supported node/date
- supports explicit compare date
- defaults compare date to previous business day
- supports history retrieval
- returns explicit statuses for missing or degraded conditions

### Data-contract

- all outputs conform to typed schemas
- nullability rules are explicit and tested
- no consumer needs to infer missingness from absent keys

### Architecture

- no agent logic
- no UI logic
- no orchestration logic
- no free-text search or fuzzy node resolution
- read-only deterministic service

### Replay

- same snapshot returns same result
- replay fixtures pass consistently

## Test cases

### Positive

- desk VaR summary with prior day and full history
- desk ES summary with prior day and full history
- book-level history retrieval over 10 days

### Negative

- nonexistent node
- unsupported measure
- invalid date range
- malformed node reference

### Edge

- previous value zero
- prior day missing
- only 3 history points available
- partial snapshot

### Replay

- fixed snapshot replay for VaR
- fixed snapshot replay for ES
- compare outputs stable across repeated runs

## Minimal fixture pack

Create a small synthetic dataset with:

- 1 firm
- 2 divisions
- 3 desks
- 2 books per desk
- 5 business dates minimum
- VaR and ES values
- at least one:
  - missing compare point
  - zero prior value
  - partial snapshot case

## Work item decomposition

### WI-1.1.1

Define core enums and schemas:

- `MeasureType`
- `SummaryStatus`
- `NodeLevel`
- `NodeRef`
- `RiskSummary`
- `RiskHistoryPoint`
- `RiskHistorySeries`

### WI-1.1.2

Implement fixture dataset and loader

### WI-1.1.3

Implement business-date comparison resolver

### WI-1.1.4

Implement `get_risk_history`

### WI-1.1.5

Implement `get_risk_summary`

### WI-1.1.6

Implement rolling statistics helper

### WI-1.1.7

Implement `get_risk_delta`

### WI-1.1.8

Add unit tests

### WI-1.1.9

Add replay tests

### WI-1.1.10

Document module README and usage examples

## Reviewer checklist

- does the PR stay inside deterministic module scope?
- are schemas explicit and typed?
- are missing/degraded states explicit?
- are delta rules correct when prior value is zero/null?
- is replayability preserved?
- are tests covering positive, edge, and degraded cases?
- has any orchestration or agent logic leaked in?

## Open questions

- do you want `ES_97_5` only in v1, or also stressed ES placeholders?
- should firm-level and division-level rows be read directly from store only, or may v1 aggregate if absent?
- do you want base currency hard-wired in v1?
- do you want a separate thin `RiskDelta` schema, or just reuse `RiskSummary`?

# PRD-1.1: Risk Summary Service v2

## Header

- **PRD ID:** PRD-1.1-v2
- **Title:** Risk Summary Service
- **Phase:** Phase 1
- **Status:** Ready for implementation
- **Module:** Risk Analytics
- **Type:** Deterministic service
- **Primary owner:** Technical Owner, Risk Analytics
- **Business owner:** Market Risk Reporting Owner
- **Control owner:** Risk Data / Controls Owner
- **Supersedes:** `PRD-1.1-risk-summary-service.md` for implementation planning

## Purpose

Provide the canonical deterministic service for retrieving daily VaR and Expected Shortfall summaries across the risk hierarchy.

This version refines the original PRD by adding explicit scope semantics for top-of-house versus legal-entity views, and by separating first-order delta moves from second-order volatility-aware risk change.

## Why this exists

Today, many downstream processes need the same core question answered:

- what is the current VaR or ES for a node?
- what changed versus the comparison date?
- what is the recent history?
- is the answer complete, partial, or degraded?
- has the node merely moved, or has its risk become more unstable?

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
- Support hierarchy scopes:
  - top of house
  - legal entity
- Support comparison to prior business day or explicit comparison date
- Return:
  - current value
  - prior value
  - absolute delta
  - percentage delta
  - rolling statistics
  - volatility-aware change flags
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
- FX conversion

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
- first-order and second-order change are distinct concepts

## Canonical concepts

### Supported measures

- `VAR_1D_99`
- `VAR_10D_99`
- `ES_97_5`

### Supported node reference

A target must be expressed as a typed hierarchy address plus scope context, not a free-text string.

A valid `node_ref` must include:

- hierarchy level
- stable node identifier
- hierarchy scope
- legal entity identifier when scope = `LEGAL_ENTITY`

### Hierarchy scope model

The service must support two hierarchy scopes:

- `TOP_OF_HOUSE`: the full firm-wide hierarchy across all included legal entities
- `LEGAL_ENTITY`: a hierarchy scoped to a single legal entity

A hierarchy path is therefore not sufficient on its own. A node reference must always be interpreted together with its scope context.

Examples:

- Top-of-house desk view: desk `Rates Macro` across the full firm
- Legal-entity desk view: desk `Rates Macro` within legal entity `LE-UK-BANK`

The same logical hierarchy levels may exist in both scopes.

### Reporting currency

- v1 returns values only in the canonical base reporting currency stored in the source snapshot
- v1 does not accept a `currency` input parameter
- v1 does not perform FX conversion

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

- if `compare_to_date` is omitted, default to prior business day as determined by the canonical risk business-day resolver
- the authoritative business-day calendar for production is the firm risk calendar used by the canonical snapshot process
- fixture and replay implementations must use the calendar pinned to the fixture or snapshot metadata
- no consumer may infer business days independently
- if `lookback_window` is omitted, use service default for rolling stats
- if `require_complete=true`, partial results must return an explicit degraded error/status
- if `snapshot_id` is provided, retrieval must be pinned to that snapshot
- if `scope_type = TOP_OF_HOUSE`, `legal_entity_id` must be null
- if `scope_type = LEGAL_ENTITY`, `legal_entity_id` is required
- node resolution must be exact within the selected scope
- a node identifier valid in one scope must not be assumed valid in another scope

## Outputs

### Primary output: `RiskSummary`

Fields:

- `node_ref` 
- `node_level` 
- `hierarchy_scope` 
- `legal_entity_id` 
- `measure_type`
- `as_of_date`
- `compare_to_date`
- `current_value`
- `previous_value`
- `delta_abs`
- `delta_pct`
- `rolling_mean`
- `rolling_std` (sample standard deviation, ddof = 1)
- `rolling_min`
- `rolling_max`
- `history_points_used`
- `status`
- `status_reasons`
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

### Secondary output: `RiskDelta`

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
- `status`
- `status_reasons`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

`RiskDelta` is a first-order change object only. It captures current value, comparison value, and direct movement. It does not by itself represent second-order volatility or regime instability.

### Secondary output: `RiskChangeProfile`

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
- `rolling_std` (sample standard deviation, ddof = 1)
- `rolling_min`
- `rolling_max`
- `volatility_regime`
- `volatility_change_flag`
- `history_points_used`
- `status`
- `status_reasons`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

### Volatility regime

Allowed values:

- `LOW`
- `NORMAL`
- `ELEVATED`
- `HIGH`
- `INSUFFICIENT_HISTORY`

### Volatility change flag

Allowed values:

- `STABLE`
- `RISING`
- `FALLING`
- `INSUFFICIENT_HISTORY`

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
- exactly one canonical status must be returned for a given response
- `status_reasons` carries secondary detail and supporting diagnostics
- status precedence is:
  1. `UNSUPPORTED_MEASURE`
  2. `MISSING_SNAPSHOT`
  3. `MISSING_NODE`
  4. `DEGRADED`
  5. `MISSING_COMPARE`
  6. `MISSING_HISTORY`
  7. `PARTIAL`
  8. `OK`

## Volatility-aware change concepts

This service distinguishes between:

- first-order change: the movement between current and comparison value
- second-order risk: the instability or variability of the series over the lookback window

First-order change is represented by absolute and percentage delta.

Second-order risk is represented by rolling dispersion and related volatility flags derived from the pinned history window.

In v1, second-order risk is descriptive and deterministic. It does not introduce stochastic forecasting or scenario simulation.

## API surface

### `get_risk_summary`

Purpose:
Return current summary plus comparison and rolling stats.

### `get_risk_history`

Purpose:
Return dated history for a node and measure.

### `get_risk_delta`

Purpose:
Return a minimal first-order delta-focused object for fast consumers.

### `get_risk_change_profile`

Purpose:
Return first-order change plus second-order volatility context for consumers that need more than a simple delta.

## Business rules

1. Current value is mandatory for a valid summary.
2. Comparison is optional unless explicitly required.
3. Percentage delta must be null when previous value is zero or null.
4. Rolling statistics must use only available valid points.
5. History must be ordered ascending by date.
6. Hierarchy references must be exact and typed.
7. This service does not aggregate from raw trades on demand in v1 unless already present in canonical store.
8. No narrative text in outputs.
9. First-order change and second-order volatility must be treated as distinct concepts.
10. A small delta does not imply low risk if rolling volatility is elevated.
11. Volatility metrics must be computed only from valid historical points within the pinned scope and snapshot context.
12. Volatility interpretation must be deterministic and rule-based in v1, with no narrative or heuristic LLM logic.
13. `volatility_regime` must be derived deterministically from rolling standard deviation and versioned threshold rules.
14. `volatility_change_flag` must be derived deterministically by comparing short-window and baseline-window dispersion measures.
15. Exact volatility thresholds must be explicitly configured and versioned.

## Degraded and error cases

### Case: current point missing

Result:

- `status = MISSING_SNAPSHOT` when the requested snapshot cannot be found
- `status = MISSING_NODE` when the snapshot exists but the node does not
- no fabricated values

### Case: compare point missing

Result:

- current value returned
- prior and deltas null
- `status = MISSING_COMPARE`

### Case: insufficient history

Result:

- current summary still returned if available
- rolling fields calculated from available points with explicit minimum thresholds:
  - mean/min/max require at least 1 point
  - std requires at least 2 points
- `status = MISSING_HISTORY`

### Case: unsupported measure

Result:

- typed validation failure or `UNSUPPORTED_MEASURE`

### Case: partial snapshot

Result:

- `status = DEGRADED`
- include reason codes

## Replay requirements

- service must support replay by `snapshot_id`
- same input plus same snapshot must yield same output
- fixtures must pin expected outputs
- replay output must not depend on wall-clock execution time
- if `generated_at` is included, it must be deterministic for a given `snapshot_id` and derived from snapshot metadata or another pinned source

## Acceptance criteria

### Functional

- returns valid VaR summary for supported node/date
- returns valid ES summary for supported node/date
- supports explicit compare date
- defaults compare date to previous business day
- supports history retrieval
- returns explicit statuses for missing or degraded conditions
- supports retrieval for both `TOP_OF_HOUSE` and `LEGAL_ENTITY` scopes
- returns distinct results for the same logical node under different legal entities when underlying data differs
- does not silently collapse legal-entity-scoped requests into top-of-house results
- supports volatility-aware change retrieval in addition to simple delta retrieval

### Data-contract

- all outputs conform to typed schemas
- nullability rules are explicit and tested
- no consumer needs to infer missingness from absent keys
- `NodeRef` includes explicit scope semantics
- first-order and second-order change outputs are distinct and typed

### Architecture

- no agent logic
- no UI logic
- no orchestration logic
- no free-text search or fuzzy node resolution
- read-only deterministic service

### Replay validation

- same snapshot returns same result
- replay fixtures pass consistently
- volatility flags are replay-stable for a pinned snapshot

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
- at least 2 legal entities
- at least one node present in multiple legal entities with different values
- at least one case with modest delta but elevated rolling volatility
- at least one case with large delta but stable volatility context

## Decisions taken for v1

- v1 supports `ES_97_5` only; stressed ES is out of scope
- firm-level and division-level rows are read directly from the canonical store in v1
- base reporting currency is hard-wired in v1
- `get_risk_delta` returns a dedicated `RiskDelta` schema
- `NodeRef` is scope-aware and supports both `TOP_OF_HOUSE` and `LEGAL_ENTITY`
- volatility-aware change is represented via `RiskChangeProfile`

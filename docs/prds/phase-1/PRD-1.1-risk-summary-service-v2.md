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
- **Supersedes:** `archive/PRD-1.1-risk-summary-service-v1-archived.md` for implementation planning

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

### Required inputs for as-of-date retrieval

- `node_ref`
- `as_of_date`
- `measure_type`

These apply to `get_risk_summary`, `get_risk_delta`, and `get_risk_change_profile`.

### Optional inputs for as-of-date retrieval

The following optional inputs apply to `get_risk_summary`, `get_risk_delta`, and `get_risk_change_profile`:

- `compare_to_date`
- `snapshot_id`

The following optional inputs apply to `get_risk_summary` and `get_risk_change_profile` only. `get_risk_delta` does not accept these inputs:

- `lookback_window`
- `require_complete`

`get_risk_history` uses the dedicated request shape defined in the API surface section below.

### Input rules

- if `compare_to_date` is omitted, default to prior business day as determined by the canonical risk business-day resolver
- the authoritative business-day calendar for production is the firm risk calendar used by the canonical snapshot process
- fixture and replay implementations must use the calendar pinned to the fixture or snapshot metadata
- no consumer may infer business days independently
- for `get_risk_summary` and `get_risk_change_profile`, if `lookback_window` is omitted, use a default lookback window of `60` business days
- `lookback_window` is measured in business days from the canonical risk calendar only, using the canonical risk business-day resolver
- for `get_risk_summary` and `get_risk_change_profile`, a `lookback_window` of `N` means a window of exactly `N` business days ending on `as_of_date`, inclusive of `as_of_date`; the start date is the `(N-1)`th prior business day from `as_of_date` per the canonical risk business-day resolver
- in v1, `get_risk_summary` and `get_risk_change_profile` accept `lookback_window` only when omitted or explicitly set to `60`; any other value is an unsupported request
- `lookback_window` and `require_complete` do not apply to `get_risk_delta`
- if `require_complete=true`, partial results must return an explicit degraded error/status
- if `snapshot_id` is provided for as-of-date retrieval, retrieval must be pinned to that snapshot
- if `hierarchy_scope = TOP_OF_HOUSE`, `legal_entity_id` must be null
- if `hierarchy_scope = LEGAL_ENTITY`, `legal_entity_id` is required
- node resolution must be exact within the selected scope
- a node identifier valid in one scope must not be assumed valid in another scope
- for `get_risk_history`, `start_date` and `end_date` define an inclusive date range
- for `get_risk_history`, `start_date` must be on or before `end_date`
- for `get_risk_history`, if `snapshot_id` is provided, it is the anchor snapshot for the request and must resolve to a snapshot whose `as_of_date` equals `end_date`
- for `get_risk_history`, `snapshot_id` pins the request context, but returned `RiskHistoryPoint.snapshot_id` values remain the per-point source snapshot ids for each returned date
- for `get_risk_history`, the pinned dataset context is the broader canonical dataset selected for the request by scope plus anchor-snapshot/date context, not only the row lookup at `end_date`
- for `get_risk_history`, node resolution is performed against that pinned dataset context across its available history
- if `snapshot_id` is omitted for `get_risk_history`, the request is anchored to the canonical dataset selected by the service for `end_date`
- for `get_risk_history`, `require_complete=true` upgrades otherwise partial history results to `DEGRADED`

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
- `hierarchy_scope`
- `legal_entity_id`
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
- `volatility_regime`
- `volatility_change_flag`
- `history_points_used`
- `status`
- `status_reasons`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

`RiskSummary`, `RiskDelta`, and `RiskChangeProfile` retain top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` as denormalized convenience fields for exports, dashboards, and downstream consumers. These fields must always mirror `node_ref` exactly. `node_ref` remains the canonical source of truth.

### Delta field semantics (normative)

The following first-order delta rules are deterministic and apply consistently to all as-of-date object outputs where delta fields exist: `RiskDelta`, `RiskSummary`, and `RiskChangeProfile`.

Definitions:

- `delta_abs = current_value - previous_value` when `previous_value` is not null
- `delta_pct = delta_abs / abs(previous_value)` when `previous_value` is not null and `previous_value != 0`

Null and zero handling:

- if `previous_value` is null, both `delta_abs` and `delta_pct` are null
- if `previous_value == 0`, `delta_abs` is computed per the rule above and `delta_pct` is null

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

## Volatility policy

### Window policy

- `baseline_window = 60` business days
- `short_window = 10` business days
- both windows are anchored on `as_of_date`
- both windows are inclusive of `as_of_date`
- both windows use only the canonical risk business-day resolver
- the baseline window applies to `get_risk_summary` rolling statistics and to `get_risk_change_profile`
- the short window applies only to `get_risk_change_profile`

### Regime calculation

For `RiskChangeProfile`, `volatility_regime` is derived from a scale-normalized dispersion ratio rather than from raw `rolling_std` alone.

Definitions:

- `reference_level = max(abs(current_value), abs(rolling_mean))`
- `volatility_ratio = rolling_std / reference_level`

Rules:

- if `reference_level == 0` and `rolling_std == 0`, classify `LOW`
- if `reference_level == 0` and `rolling_std > 0`, classify `HIGH`
- otherwise apply these bands:
  - `LOW` when `volatility_ratio < 0.05`
  - `NORMAL` when `0.05 <= volatility_ratio < 0.15`
  - `ELEVATED` when `0.15 <= volatility_ratio < 0.30`
  - `HIGH` when `volatility_ratio >= 0.30`

### Change-flag calculation

For `RiskChangeProfile`, `volatility_change_flag` is derived from short-window versus baseline-window dispersion.

Definitions:

- `short_std` = sample standard deviation over the 10-business-day short window
- `baseline_std` = sample standard deviation over the 60-business-day baseline window

Rules:

- if `baseline_std == 0` and `short_std == 0`, classify `STABLE`
- if `baseline_std == 0` and `short_std > 0`, classify `RISING`
- otherwise compute `dispersion_change_ratio = short_std / baseline_std`
- apply these bands:
  - `FALLING` when `dispersion_change_ratio <= 0.80`
  - `STABLE` when `0.80 < dispersion_change_ratio < 1.20`
  - `RISING` when `dispersion_change_ratio >= 1.20`

### Minimum-history rules

- `rolling_mean`, `rolling_min`, and `rolling_max` require at least 1 valid point
- `rolling_std` requires at least 2 valid points
- `volatility_regime` requires at least 20 valid points in the 60-business-day baseline window, otherwise `INSUFFICIENT_HISTORY`
- `volatility_change_flag` requires at least 5 valid points in the 10-business-day short window and at least 20 valid points in the 60-business-day baseline window, otherwise `INSUFFICIENT_HISTORY`
- degraded or invalid historical rows are excluded from volatility calculations
- if exclusions reduce the valid-point count below the required minimum, the affected volatility output must be `INSUFFICIENT_HISTORY`

## Status model

Canonical status vocabulary across service operations:

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
- exactly one canonical status must be returned for a given response or typed service error
- `status_reasons` carries secondary detail and supporting diagnostics
- this vocabulary is shared across object-returning outcomes and typed service-error outcomes; it does not imply that every status is representable inside every returned object
- typed request validation failures sit outside returned-object status encoding and must not fabricate `RiskDelta`, `RiskSummary`, or `RiskChangeProfile` objects
- this PRD governs which canonical outcome category applies; it does not redesign the repository's shared typed service-error or request-validation envelope
- for `get_risk_delta`, `get_risk_summary`, and `get_risk_change_profile`, a typed object is returned only when a current scoped point exists and the required current-value plus replay/version fields can be populated honestly
- for `get_risk_delta` in v1, reachable in-object statuses are `OK`, `DEGRADED`, and `MISSING_COMPARE`
- for `get_risk_summary` and `get_risk_change_profile` in v1, reachable in-object statuses are `OK`, `DEGRADED`, `MISSING_COMPARE`, and `MISSING_HISTORY`
- for as-of-date retrieval in v1, `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, and `MISSING_NODE` are typed service-error outcomes, not partially populated `RiskDelta`, `RiskSummary`, or `RiskChangeProfile` objects
- for as-of-date retrieval in v1, `PARTIAL` is not returned inside `RiskDelta`, `RiskSummary`, or `RiskChangeProfile`; it remains available for operation-specific use such as `RiskHistorySeries`
- for `RiskSummary` and `RiskChangeProfile`, conditions that would produce `PARTIAL` on an underlying history retrieval, such as sparse valid points in range, must be surfaced as in-object `DEGRADED` rather than `PARTIAL`
- as-of-date retrieval outcome precedence is:
  1. typed request validation failure
  2. typed service error `UNSUPPORTED_MEASURE`
  3. typed service error `MISSING_SNAPSHOT`
  4. typed service error `MISSING_NODE`
  5. in-object `DEGRADED`
  6. in-object `MISSING_COMPARE`
  7. in-object `MISSING_HISTORY`
  8. in-object `OK`

For `RiskHistorySeries`, status precedence is:

1. `UNSUPPORTED_MEASURE`
2. `MISSING_SNAPSHOT`
3. `MISSING_NODE`
4. `DEGRADED`
5. `MISSING_HISTORY`
6. `PARTIAL`
7. `OK`

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

Inputs:

- `node_ref`
- `as_of_date`
- `measure_type`
- `compare_to_date=None`
- `lookback_window=60`
- `require_complete=False`
- `snapshot_id=None`

Returns:

- `RiskSummary` when a current scoped point exists for the requested `as_of_date`
- typed service error `UNSUPPORTED_MEASURE` when the requested `measure_type` is outside this operation's governed contract
- typed service error `MISSING_SNAPSHOT` or `MISSING_NODE` when no current scoped point can be returned honestly
- typed request validation failure for invalid request inputs

The default `lookback_window=60` applies here as 60 business days ending on `as_of_date`, inclusive of `as_of_date`.

### `get_risk_history`

Purpose:
Return dated history for a node and measure.

Inputs:

- `node_ref`
- `measure_type`
- `start_date`
- `end_date`
- `require_complete=False`
- `snapshot_id=None`

Returns:

- `RiskHistorySeries`

### `get_risk_delta`

Purpose:
Return a minimal first-order delta-focused object for fast consumers.

Inputs:

- `node_ref`
- `as_of_date`
- `measure_type`
- `compare_to_date=None`
- `snapshot_id=None`

Returns:

- `RiskDelta` when a current scoped point exists for the requested `as_of_date`
- typed service error `UNSUPPORTED_MEASURE` when the requested `measure_type` is outside this operation's governed contract
- typed service error `MISSING_SNAPSHOT` or `MISSING_NODE` when no current scoped point can be returned honestly
- typed request validation failure for invalid request inputs

### `get_risk_change_profile`

Purpose:
Return first-order change plus second-order volatility context for consumers that need more than a simple delta.

Inputs:

- `node_ref`
- `as_of_date`
- `measure_type`
- `compare_to_date=None`
- `lookback_window=60`
- `require_complete=False`
- `snapshot_id=None`

Returns:

- `RiskChangeProfile` when a current scoped point exists for the requested `as_of_date`
- typed service error `UNSUPPORTED_MEASURE` when the requested `measure_type` is outside this operation's governed contract
- typed service error `MISSING_SNAPSHOT` or `MISSING_NODE` when no current scoped point can be returned honestly
- typed request validation failure for invalid request inputs

The default `lookback_window=60` applies here as 60 business days ending on `as_of_date`, inclusive of `as_of_date`.

## Business rules

1. Current value is mandatory for a valid summary.
2. Comparison is optional unless explicitly required.
3. For `RiskDelta`, `RiskSummary`, and `RiskChangeProfile`, `delta_abs` must equal `current_value - previous_value` whenever `previous_value` is not null.
4. For `RiskDelta`, `RiskSummary`, and `RiskChangeProfile`, `delta_pct` must equal `delta_abs / abs(previous_value)` whenever `previous_value` is not null and `previous_value != 0`.
5. For `RiskDelta`, `RiskSummary`, and `RiskChangeProfile`, if `previous_value` is null then both `delta_abs` and `delta_pct` must be null.
6. For `RiskDelta`, `RiskSummary`, and `RiskChangeProfile`, if `previous_value == 0` then `delta_abs` remains computed and `delta_pct` must be null.
7. Rolling statistics must use only available valid points.
8. History must be ordered ascending by date.
9. Hierarchy references must be exact and typed.
10. This service does not aggregate from raw trades on demand in v1 unless already present in canonical store.
11. No narrative text in outputs.
12. First-order change and second-order volatility must be treated as distinct concepts.
13. A small delta does not imply low risk if rolling volatility is elevated.
14. Volatility metrics must be computed only from valid historical points within the pinned scope and snapshot context.
15. Volatility interpretation must be deterministic and rule-based in v1, with no narrative or heuristic LLM logic.
16. `volatility_regime` must be derived deterministically from the normalized `volatility_ratio` defined in the volatility policy.
17. `volatility_change_flag` must be derived deterministically from the `dispersion_change_ratio` defined in the volatility policy.
18. Exact volatility thresholds, window lengths, anchor semantics, inclusivity, and minimum-history gates are part of the governed volatility policy and must be versioned.

## Degraded and error cases

### Case: invalid as-of-date request

Result:

- typed request validation failure
- no `RiskDelta`, `RiskSummary`, or `RiskChangeProfile` is returned
- examples include invalid explicit `compare_to_date`, invalid or blank `snapshot_id`, unsupported `lookback_window` or `require_complete` usage for the operation, and any other request that fails typed-contract or canonical business-day validation

### Case: invalid history date range

Result:

- typed request validation failure
- no `RiskHistorySeries` is returned

### Case: current point missing

Result:

- for `get_risk_delta`, `get_risk_summary`, and `get_risk_change_profile`, no object is returned when the current point is missing
- typed service error `MISSING_SNAPSHOT` when the requested current snapshot cannot be found
- typed service error `MISSING_NODE` when the current snapshot exists but the scoped node cannot be resolved for the requested `as_of_date`
- no fabricated values

This rule applies because `RiskDelta`, `RiskSummary`, and `RiskChangeProfile` all require current-value and replay/version metadata that cannot be populated honestly when the current scoped point is absent.

### Case: compare point missing

Result:

- for `get_risk_delta`, `get_risk_summary`, and `get_risk_change_profile`, current value returned when the current point exists
- prior and deltas null
- `status = MISSING_COMPARE`

### Case: insufficient history

Result:

- current `RiskSummary` or `RiskChangeProfile` still returned if the current point exists
- rolling fields calculated from available points with explicit minimum thresholds:
  - mean/min/max require at least 1 point
  - std requires at least 2 points
- `status = MISSING_HISTORY`

### Case: history snapshot missing

Result:

- `status = MISSING_SNAPSHOT`
- `points = []`

### Case: history node missing

Result:

- `status = MISSING_NODE`
- `points = []`

`MISSING_NODE` means the requested scoped node and measure cannot be resolved anywhere in the pinned dataset context for the history request.

### Case: no history points in requested range

Result:

- `status = MISSING_HISTORY`
- `points = []`

`MISSING_HISTORY` means the requested scoped node and measure resolve in the pinned dataset context, but zero returnable points fall within the inclusive requested range.

This status is reachable in v1 when the node exists elsewhere in the pinned dataset context but has no returnable points inside the requested date range.

### Case: sparse history points in requested range

Result:

- available valid points returned in ascending date order
- `status = PARTIAL`

### Case: degraded history rows in requested range

Result:

- available points returned in ascending date order
- `status = DEGRADED`
- include reason codes for degraded dates or snapshots

### Case: `require_complete=true` for history retrieval

Result:

- any history result that would otherwise be `PARTIAL` must return `status = DEGRADED`
- available ordered points may still be returned

### Case: unsupported measure

Result:

- for `get_risk_delta`, `get_risk_summary`, and `get_risk_change_profile`, typed service error `UNSUPPORTED_MEASURE` for a supported request shape that asks for a measure outside the governed operation contract
- for `get_risk_history`, `UNSUPPORTED_MEASURE` remains an operation status on `RiskHistorySeries` exactly as defined in the history-status model above
- typed request validation failure only when the request itself is structurally invalid

### Case: partial snapshot

Result:

- when the current scoped point exists and required object fields can still be populated honestly, return the typed object with `status = DEGRADED`
- include reason codes

## Replay requirements

- service must support replay by `snapshot_id`
- same input plus same snapshot must yield same output
- fixtures must pin expected outputs
- replay output must not depend on wall-clock execution time
- if `generated_at` is included, it must be deterministic for a given `snapshot_id` and derived from snapshot metadata or another pinned source
- the v1 volatility policy ruleset identifier is `VOLATILITY_RULES_V1`
- v1 does not allow runtime overrides for volatility thresholds, window lengths, anchor semantics, inclusivity, or minimum-history rules
- for v1, the effective volatility-policy version is carried by `service_version`
- any change to volatility bands, window lengths, business-day basis, anchor semantics, inclusivity, or minimum-history rules requires a `service_version` bump and replay-fixture refresh
- ADR-003 application for this v1 service slice is approved as follows: each output contract retains the replay/version metadata explicitly defined in its field list, but the service must not invent module-local evidence or trace fields
- explicit typed evidence-reference and trace-context fields are deferred until a dedicated shared-contract slice defines the canonical repo-wide objects for them
- until then, replayability and auditability for this service are satisfied by pinned request context in replay fixtures and replay test artifacts, plus the replay/version metadata already defined on each output contract
- pinned request context means the fully resolved request values that affect deterministic output
- the minimum pinned request-context elements for this service are:
  - operation variant invoked (`get_risk_summary`, `get_risk_delta`, `get_risk_history`, or `get_risk_change_profile`)
  - `node_ref`
  - `as_of_date`
  - `measure_type`
  - explicit `compare_to_date`, or the resolved comparison date after service defaulting
  - `lookback_window` when relevant
  - history range bounds when relevant
  - `require_complete`
  - `snapshot_id` when provided
- for volatility-aware outputs, replay fixtures and replay tests must pin the effective window policy explicitly:
  - `baseline_window = 60`
  - `short_window = 10`
  - business-day basis
  - inclusive anchor on `as_of_date`
- for `get_risk_history`, pinned request context must include `start_date`, `end_date`, `require_complete`, and `snapshot_id` when provided
- for `get_risk_history`, when `snapshot_id` is provided, it is the anchor snapshot for the request and must remain explicit in replay fixtures and replay test artifacts
- this deferral does not expand `RiskHistoryPoint` or `RiskHistorySeries` metadata beyond the fields explicitly listed in their v1 contracts
- `status_reasons` must not be used as a substitute for structured evidence references

## Logging and evidence

- typed outputs and replay artifacts remain the canonical evidence surfaces for this service
- logs may mirror request, status, and replay context, but logs must not replace replay artifacts or typed evidence/replay metadata
- minimum structured logging should include:
  - request or correlation id
  - operation variant
  - `node_ref`
  - `measure_type`
  - `as_of_date`, or `start_date` and `end_date` for history retrieval
  - `compare_to_date` when relevant
  - resolved `lookback_window` when relevant
  - `snapshot_id` when provided
  - returned `status`
  - `history_points_used` when relevant
  - duration

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

## Test cases

### Positive

- valid `get_risk_summary` retrieval with default `lookback_window`
- valid `get_risk_delta` retrieval for an explicit compare date
- valid `get_risk_delta` retrieval with compare date defaulting applied deterministically
- valid `get_risk_change_profile` retrieval with default `lookback_window`
- valid `get_risk_history` retrieval over an explicit inclusive date range

### Negative

- unsupported measure
- missing snapshot
- missing node

### Edge

- prior value equals zero
- prior value is negative (percentage denominator uses `abs(previous_value)`)
- sparse history in requested range
- degraded snapshot rows
- explicit `lookback_window` overriding the default

### Replay cases

- same pinned snapshot and same resolved request context reproduce the same result
- replay fixtures pin default and explicit `lookback_window` behavior deterministically

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

## Work item decomposition

Implementation sequencing is governed by the active `work_items/` canon rather than a duplicated decomposition appendix in this PRD.

For v1, the governed slices cover:

- schemas and enums
- deterministic fixtures
- history retrieval
- first-order core retrieval
- rolling statistics and replay
- business-day resolution

## Decisions taken for v1

- v1 continues to support VaR measures; for ES, v1 supports `ES_97_5` only, and stressed ES is out of scope
- firm-level and division-level rows are read directly from the canonical store in v1
- base reporting currency is hard-wired in v1
- `get_risk_delta` returns a dedicated `RiskDelta` schema
- `NodeRef` is scope-aware and supports both `TOP_OF_HOUSE` and `LEGAL_ENTITY`
- volatility-aware change is represented via `RiskChangeProfile`

## Reviewer checklist

- verify contract fidelity for `get_risk_summary`, `get_risk_delta`, `get_risk_history`, and `get_risk_change_profile`
- verify default `lookback_window` semantics, including unit, anchor, inclusivity, and explicit override behavior
- verify degraded and missing status behavior remains explicit and typed
- verify replay/version metadata is preserved without inventing ad hoc evidence or trace fields
- verify no hidden aggregation logic or scope collapse is introduced

## Open questions

- none for current v1 implementation planning

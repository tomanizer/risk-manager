# PRD-1.1-v2 Foundation Implementation Slice

## Purpose

This document turns the next implementation step for `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md` into a coding-agent-ready delivery slice.

It covers the first foundation PR for the Risk Summary module.

## Scope of the foundation PR

The recommended first implementation PR should include:

- WI-1.1.1 schemas and enums
- WI-1.1.2 deterministic fixtures
- WI-1.1.3 business-day resolver

This order is intentional:

- contracts first
- fixture fuel second
- canonical business-day logic before service retrieval logic

## Delivery target

Create the deterministic foundation needed for later work on:

- `get_risk_history`
- `get_risk_delta`
- `get_risk_summary`
- `get_risk_change_profile`

## Slice A: WI-1.1.1 Schemas and enums

### Goal

Create the canonical typed contracts for the Risk Summary module.

### Suggested files

- `src/modules/risk_analytics/contracts/enums.py`
- `src/modules/risk_analytics/contracts/node_ref.py`
- `src/modules/risk_analytics/contracts/history.py`
- `src/modules/risk_analytics/contracts/summary.py`
- `src/modules/risk_analytics/contracts/__init__.py`
- `tests/unit/modules/risk_analytics/test_enums.py`
- `tests/unit/modules/risk_analytics/test_node_ref.py`
- `tests/unit/modules/risk_analytics/test_contracts.py`

### Required enums

- `MeasureType`
  - `VAR_1D_99`
  - `VAR_10D_99`
  - `ES_97_5`
- `HierarchyScope`
  - `TOP_OF_HOUSE`
  - `LEGAL_ENTITY`
- `NodeLevel`
  - `FIRM`
  - `DIVISION`
  - `AREA`
  - `DESK`
  - `BOOK`
  - `POSITION`
  - `TRADE`
- `SummaryStatus`
  - `OK`
  - `PARTIAL`
  - `MISSING_COMPARE`
  - `MISSING_HISTORY`
  - `MISSING_NODE`
  - `MISSING_SNAPSHOT`
  - `UNSUPPORTED_MEASURE`
  - `DEGRADED`
- `VolatilityRegime`
  - `LOW`
  - `NORMAL`
  - `ELEVATED`
  - `HIGH`
  - `INSUFFICIENT_HISTORY`
- `VolatilityChangeFlag`
  - `STABLE`
  - `RISING`
  - `FALLING`
  - `INSUFFICIENT_HISTORY`

### Required structures

#### `NodeRef`

Fields:

- `hierarchy_scope`
- `legal_entity_id: str | None`
- `node_level`
- `node_id`
- `node_name: str | None = None`

Validation rules:

- if `hierarchy_scope == TOP_OF_HOUSE`, `legal_entity_id` must be `None`
- if `hierarchy_scope == LEGAL_ENTITY`, `legal_entity_id` must be non-null and non-empty
- `node_level == FIRM` is only valid with `TOP_OF_HOUSE`
- `LEGAL_ENTITY` scope should restrict `node_level` to `DIVISION` or below unless a later ADR explicitly broadens that contract

#### `RiskHistoryPoint`

- `node_ref`
- `measure_type`
- `date`
- `value`
- `snapshot_id`
- `status`

#### `RiskHistorySeries`

- `node_ref`
- `measure_type`
- `start_date`
- `end_date`
- `points`
- `status`
- `status_reasons`
- `service_version`

#### `RiskDelta`

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

The top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` fields are retained as denormalized convenience fields for exports, dashboards, and downstream consumers. They must always mirror `node_ref` exactly.

The contract for `delta_pct` is:

- `delta_pct = delta_abs / previous_value` when `previous_value` is non-null and non-zero
- `delta_pct = null` when `previous_value` is null or zero

#### `RiskSummary`

`RiskDelta` plus:

- `rolling_mean`
- `rolling_std`
- `rolling_min`
- `rolling_max`
- `history_points_used`

#### `RiskChangeProfile`

`RiskSummary` plus:

- `volatility_regime`
- `volatility_change_flag`

### Acceptance criteria

- all enums exist and are importable from the contract package
- `NodeRef` validation works for both valid and invalid scope combinations
- all contracts instantiate cleanly
- unit tests cover invalid `NodeRef` combinations
- `delta_pct` zero-handling is explicit and tested
- no service logic is included yet

## Slice B: WI-1.1.2 Deterministic fixture pack

### Goal

Create a deterministic synthetic fixture pack for development and replay tests.

### Suggested files

- `fixtures/risk_analytics/risk_summary_fixture_pack.json`
- `src/modules/risk_analytics/fixtures/loader.py`
- `src/modules/risk_analytics/fixtures/__init__.py`
- `tests/unit/modules/risk_analytics/test_fixture_loader.py`

### Fixture requirements

#### Time

- at least 5 business dates

#### Scope

- `TOP_OF_HOUSE`
- at least 2 `LEGAL_ENTITY` values

#### Hierarchy

At minimum:

- 1 firm
- 2 divisions
- 3 desks
- 2 books per desk

#### Cases that must exist

- same logical desk in two legal entities with different values
- missing compare point
- prior value equals 0
- degraded snapshot
- modest delta with elevated volatility
- large delta with stable volatility

### Suggested top-level shape

- `service_version`
- `data_version`
- `calendar`
- `snapshots`

Each snapshot should contain:

- `snapshot_id`
- `as_of_date`
- `is_degraded`
- `rows`

### Loader behavior

Provide a small loader that:

- reads the fixture JSON
- indexes by snapshot, date, scope, node, and measure
- exposes simple helper accessors for later service code

### Acceptance criteria

- fixture file loads successfully
- fixture integrity tests pass
- all required edge cases are present
- deterministic indexing helpers exist

## Slice C: WI-1.1.3 Business-day resolver

### Goal

Implement canonical prior-business-day resolution.

### Suggested files

- `src/modules/risk_analytics/time/business_day_resolver.py`
- `src/modules/risk_analytics/time/__init__.py`
- `tests/unit/modules/risk_analytics/test_business_day_resolver.py`

### Required behavior

Provide functions such as:

- `resolve_prior_business_day(as_of_date, calendar)`
- `resolve_compare_to_date(as_of_date, compare_to_date, calendar)`

### Rules

- if explicit `compare_to_date` is provided, return it unchanged
- otherwise return prior business day from the supplied canonical calendar
- no consumer-side date guessing
- behavior must be deterministic using the supplied calendar only

### Edge cases

- missing previous business date in the supplied calendar
- as-of date not in calendar
- earliest business date in calendar

### Acceptance criteria

- prior business day resolves correctly
- explicit compare date bypasses defaulting
- failures are explicit, not silent
- tests cover weekend-like gaps via calendar holes

## Suggested PR structure

### Commit 1

Add risk analytics contracts and enums

### Commit 2

Add deterministic risk analytics fixture pack and loader

### Commit 3

Add business-day resolver for risk summary services

### Commit 4

Add unit tests for contracts, fixtures, and business-day resolution

## Coding-agent brief

Use this implementation brief:

- implement only the foundation PR scope
- keep everything deterministic and narrow
- do not implement retrieval logic yet
- preserve scope-aware hierarchy semantics
- add unit tests with the code
- do not redesign architecture
- keep `RiskDelta` first-order only
- keep `RiskChangeProfile` separate
- make business-day resolution depend only on the supplied canonical calendar

## Reviewer focus

- `NodeRef` validation correctness
- fixture completeness
- explicit degraded and missing semantics
- no service logic leaking into the foundation slice
- clean dependency base for WI-1.1.3 and WI-1.1.4

# Risk Analytics Data Structures

## Purpose

This document summarizes the intended core data structures for the first module slice.

## Enumerations

### `MeasureType`

Allowed values:

- `VAR_1D_99`
- `VAR_10D_99`
- `ES_97_5`

### `HierarchyScope`

Allowed values:

- `TOP_OF_HOUSE`
- `LEGAL_ENTITY`

### `NodeLevel`

Representative values:

- `FIRM`
- `DIVISION`
- `AREA`
- `DESK`
- `BOOK`
- `POSITION`
- `TRADE`

### `SummaryStatus`

Allowed values:

- `OK`
- `PARTIAL`
- `MISSING_COMPARE`
- `MISSING_HISTORY`
- `MISSING_NODE`
- `MISSING_SNAPSHOT`
- `UNSUPPORTED_MEASURE`
- `DEGRADED`

### `VolatilityRegime`

Allowed values:

- `LOW`
- `NORMAL`
- `ELEVATED`
- `HIGH`
- `INSUFFICIENT_HISTORY`

### `VolatilityChangeFlag`

Allowed values:

- `STABLE`
- `RISING`
- `FALLING`
- `INSUFFICIENT_HISTORY`

## Core objects

### `NodeRef`

Purpose:
Identify a hierarchy node together with its scope semantics.

Expected fields:

- `hierarchy_scope`
- `legal_entity_id` nullable for `TOP_OF_HOUSE`
- `node_level`
- `node_id`
- `node_name` optional

### `RiskHistoryPoint`

Purpose:
Single dated risk observation.

Expected fields:

- `node_ref`
- `measure_type`
- `date`
- `value`
- `snapshot_id`
- `status`

### `RiskHistorySeries`

Purpose:
History retrieval result.

Expected fields:

- `node_ref`
- `measure_type`
- `start_date`
- `end_date`
- `points`
- `status`
- `status_reasons`
- `service_version`

### `RiskDelta`

Purpose:
Minimal first-order comparison object.

Expected fields:

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

### `RiskSummary`

Purpose:
Main service answer for current-versus-prior with rolling context.

Expected fields:

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
- `rolling_std`
- `rolling_min`
- `rolling_max`
- `history_points_used`
- `status`
- `status_reasons`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

### `RiskChangeProfile`

Purpose:
First-order movement plus second-order volatility-aware context.

Expected fields:

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
- `rolling_std`
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

## Structural notes

### Why promote scope fields to top level

Although `node_ref` carries scope semantics, the top-level outputs should also expose:

- `hierarchy_scope`
- `legal_entity_id`

This makes downstream consumption easier for:

- dashboards
- walkers
- governance packs
- tabular exports

### Why keep `RiskDelta` separate from `RiskChangeProfile`

A simple delta object should remain narrow and predictable.

`RiskChangeProfile` exists because a risk manager also needs second-order context such as volatility and instability. Keeping them separate avoids overloading one contract with two different jobs.

## Fixture expectations

The fixture pack should contain:

- at least two legal entities
- a repeated logical node in multiple legal entities
- a modest-delta but high-volatility case
- a large-delta but stable-volatility case
- a zero-prior case
- a missing-compare case
- a degraded snapshot case

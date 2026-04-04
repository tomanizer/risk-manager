# Risk Analytics Service Contracts

## Purpose

This document captures the canonical service contracts for the first module slice.

## Core service surface

### `get_risk_history`

Returns a dated history series for a node, measure, scope, and date range.

Expected inputs:

- `node_ref`
- `measure_type`
- `start_date`
- `end_date`
- `snapshot_id` optional

Expected behavior:

- validate date range
- resolve node exactly within scope
- retrieve ordered history ascending by date
- pin to snapshot when provided
- return explicit status when history, node, or snapshot is missing

### `get_risk_delta`

Returns a minimal first-order comparison object.

Expected inputs:

- `node_ref`
- `measure_type`
- `as_of_date`
- `compare_to_date` optional
- `snapshot_id` optional

Expected behavior:

- default comparison to prior business day when omitted
- compute `current_value`, `previous_value`, `delta_abs`, `delta_pct`
- set `delta_pct` to null when prior is null or zero
- return only statuses relevant to first-order comparison

### `get_risk_summary`

Returns the main current-versus-prior summary with rolling context.

Expected inputs:

- `node_ref`
- `measure_type`
- `as_of_date`
- `compare_to_date` optional
- `lookback_window` optional
- `require_complete` optional
- `snapshot_id` optional

Expected behavior:

- resolve comparison date
- retrieve current point
- retrieve comparison point
- retrieve lookback history
- compute rolling stats from valid points
- expose explicit status, reasons, and metadata

### `get_risk_change_profile`

Returns first-order change plus second-order volatility-aware context.

Expected inputs:

- `node_ref`
- `measure_type`
- `as_of_date`
- `compare_to_date` optional
- `lookback_window` optional
- `snapshot_id` optional

Expected behavior:

- include first-order outputs from delta logic
- compute rolling dispersion context
- derive `volatility_regime`
- derive `volatility_change_flag`
- preserve replay determinism

## Input contract notes

### Node reference

A `NodeRef` must carry:

- `hierarchy_scope`
- `legal_entity_id` when scope is `LEGAL_ENTITY`
- `node_level`
- `node_id`
- optional display name

### Measure type

Supported measures in the first slice:

- `VAR_1D_99`
- `VAR_10D_99`
- `ES_97_5`

### Snapshot pinning

All services must accept optional `snapshot_id` pinning.

When pinned:

- retrieval must not drift to a newer snapshot
- replay must remain stable
- `generated_at` must be deterministic from pinned metadata

## Status rules

### Summary status family

Allowed top-level statuses:

- `OK`
- `PARTIAL`
- `MISSING_COMPARE`
- `MISSING_HISTORY`
- `MISSING_NODE`
- `MISSING_SNAPSHOT`
- `UNSUPPORTED_MEASURE`
- `DEGRADED`

### Recommended precedence

1. `UNSUPPORTED_MEASURE`
2. `MISSING_SNAPSHOT`
3. `MISSING_NODE`
4. `DEGRADED`
5. `MISSING_COMPARE`
6. `MISSING_HISTORY`
7. `PARTIAL`
8. `OK`

### Delta-specific status discipline

`RiskDelta` should not use history-specific statuses when no history is needed.

Recommended delta-appropriate statuses:

- `OK`
- `MISSING_COMPARE`
- `MISSING_NODE`
- `MISSING_SNAPSHOT`
- `UNSUPPORTED_MEASURE`
- `DEGRADED`

## Contract invariants

### General invariants

- no free-text node resolution
- no hidden FX conversion
- no silent scope collapse
- all outputs include service metadata
- all degraded states are explicit

### Mathematical invariants

- `delta_abs = current_value - previous_value` when both exist
- `delta_pct = delta_abs / previous_value` only when previous value is non-null and non-zero
- `rolling_std` uses sample standard deviation with `ddof = 1`
- rolling metrics use only valid points in the pinned context

### History invariants

- history points ordered ascending by date
- no duplicate date rows for the same pinned retrieval context
- missing dates are not fabricated silently

## Decision use

These contracts are intended to support:

- daily monitoring
- initial risk investigation
- hierarchy localization
- second-order volatility review
- management and governance pack preparation

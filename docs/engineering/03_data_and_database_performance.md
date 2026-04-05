# Data And Database Performance

## Purpose

This document defines the default data-path and database-performance preferences for the repository.

## Analytical database rule

For analytical and risk-style workloads, prefer columnar and SQL-friendly execution over row-oriented abstraction layers.

## Preferred data-path choices

### `duckdb`

Use `duckdb` for:

- local analytical queries
- fixture exploration
- filtering, joining, grouping, and aggregation over tabular data
- Arrow-backed analytical flows

### `pyarrow`

Use `pyarrow` for:

- columnar in-memory representation
- efficient interchange between subsystems
- zero-copy or low-copy handoff where possible
- Parquet and Arrow-native workflows

### `numpy`

Use `numpy` for:

- dense numerical arrays
- vectorized transforms
- numerical hot paths after tabular selection is complete

## Avoid ORM-first analytical design

Do not default to ORM-heavy access patterns for analytical services.

That style often introduces:

- row-by-row access
- avoidable object materialization
- hidden query inefficiency
- poor control over scan cost

## Database-performance questions the coding agent should ask

1. Can this filter, join, or aggregation run in SQL instead of Python?
2. Can the data stay in Arrow or columnar form longer?
3. Am I scanning more than I need?
4. Am I materializing intermediate results unnecessarily?
5. Is the access pattern replay-friendly and deterministic?

## Data-shape rule

Choose the execution substrate that matches the shape of the work:

- SQL/`duckdb` for relational transformations
- `pyarrow` for columnar interchange and file access
- `numpy` for dense numerical transforms

Do not force all three layers into every slice if one is enough.

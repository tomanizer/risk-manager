# Performance And Vectorization

## Purpose

This document defines the coding agent's default approach to performance-sensitive analytical Python.

## Performance is a first-class concern

For this repository, performance is not an afterthought.

Coding agents should think about:

- algorithmic complexity
- memory layout and copying
- database scan cost
- serialization boundaries
- vectorization opportunities
- repeated work across hot paths

## Preferred computation shapes

Prefer, in order of likelihood for analytical workloads:

- vectorized `numpy` operations
- `duckdb` SQL over columnar data
- `pyarrow` columnar tables and record batches
- `scipy` / `statsmodels` routines for statistical work
- plain Python loops only when the workload is genuinely small or inherently sequential

## Vectorization rule

If the work is array-shaped or column-shaped, default to a vectorized or set-based implementation.

Do not reach first for:

- Python `for` loops over rows
- row-wise DataFrame `.apply(...)`
- repeated object allocation inside tight loops

unless there is a clear reason that vectorization would be worse.

## When loops are acceptable

Loops are acceptable when:

- the data volume is small and bounded
- the logic is truly sequential
- the vectorized form would be materially less readable for no real gain
- the loop is outside the hot path

## Copies and conversion boundaries

Performance-sensitive code should minimize:

- repeated conversion between Python objects and columnar buffers
- repeated materialization of intermediate tables
- repeated serialization and deserialization
- unnecessary DataFrame <-> Arrow <-> list churn

## Hot-path rule

If a path is expected to scale with history length, scenario count, position count, or factor count:

- say what computation shape is used
- prefer columnar or vectorized execution
- avoid hidden quadratic behavior

## Practical guidance

- push scans, filters, joins, grouping, and aggregations into `duckdb` when that is the natural shape
- use `numpy` for dense numerical transforms
- keep data columnar as long as possible
- comment on non-obvious performance choices briefly and explicitly

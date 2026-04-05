# Library Selection And Dependency Policy

## Purpose

This document defines the repository's default preference for established Python libraries over custom reinvention.

## Default library preference

Where the workload fits, prefer established, widely used libraries such as:

- `numpy`
- `scipy`
- `pyarrow`
- `duckdb`
- `statsmodels`
- `pandas` for interface or glue work, while preferring `duckdb` and `pyarrow` for hot analytical paths

Use them directly and idiomatically where possible when they are already approved and available in the repository environment.

If one of these libraries is needed but not yet available, make that an explicit dependency change by updating `requirements.txt`, give a short justification, and verify the addition in CI.

## Approved compute stack status

The `[compute]` extra in `pyproject.toml` is an approved optional analytical stack, not the default repository CI baseline.

That means:

- coding agents may prefer these libraries when the active environment already includes them
- coding agents must not assume they are present in every CI run or every local environment by default
- if a new slice truly depends on one of them, make that dependency explicit in the package metadata and validate it in CI for that slice
- until the first governed in-repo consumer lands, treat the compute extra as approved capacity rather than universally provisioned baseline tooling

## Reinvention rule

Do not implement custom numerical, statistical, or columnar infrastructure when an established library already provides a well-understood solution.

Examples of what not to reinvent lightly:

- array math
- descriptive statistics
- linear algebra
- time-series transforms
- SQL execution
- columnar table handling

## Thin-wrapper rule

Do not add custom wrappers around these libraries unless the wrapper provides clear repository-specific value such as:

- a stable typed boundary
- explicit replay semantics
- canonical validation behavior

Even then, keep the wrapper thin and obvious.

## Library-fit guidance

### `numpy`

Default for dense vectorized numerical work.

### `scipy`

Use for established numerical and scientific routines rather than bespoke implementations.

### `statsmodels`

Use for time-series or statistical modeling tasks where its routines fit the governed method.

### `pandas`

Use for interface, interoperability, or light tabular glue where it is the simplest fit.

Do not assume it is the default hot-path engine for analytical workloads.

### `pyarrow`

Use for columnar representation, Arrow interchange, and Parquet-oriented flows.

### `duckdb`

Use for embedded analytical SQL and Arrow-backed local query execution.

## Dependency discipline

Prefer a small number of strong dependencies over:

- a larger number of overlapping libraries
- local mini-frameworks
- premature generalization layers

Every new dependency should have a concrete reason, a corresponding `requirements.txt` update, and CI validation.

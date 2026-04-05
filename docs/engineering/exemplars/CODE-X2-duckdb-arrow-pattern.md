# CODE-X2: DuckDB And Arrow Pattern

## Purpose

This example shows the preferred implementation shape for local analytical tabular processing.

## Preferred shape

- keep tabular data in Arrow-compatible form where practical
- query it with `duckdb` when filtering, joining, grouping, or aggregating
- convert to `numpy` only when the remaining work is dense numerical math
- keep the conversion boundaries explicit

## Why this is good

- it matches the natural shape of analytical workloads
- it minimizes row-by-row Python processing
- it supports clear replay and fixture-driven local testing

## What to avoid

- materializing many intermediate Python objects
- using a row-oriented abstraction layer for local analytical scans
- repeatedly moving data between Arrow, DataFrame, list, and dict forms without need

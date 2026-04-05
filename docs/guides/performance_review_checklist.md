# Performance Review Checklist

## Purpose

Use this checklist when reviewing performance-sensitive coding work.

## Computation shape

- Is the heavy work vectorized, columnar, or SQL-based where appropriate?
- Did the implementation avoid row-by-row processing on analytical data?
- Is the chosen execution substrate appropriate: `numpy`, `duckdb`, `pyarrow`, `scipy`, `statsmodels`, or a simple loop where justified?

## Data movement

- Are conversions and copies minimized?
- Does the code avoid repeated materialization of intermediate results?
- Is the columnar path preserved as long as practical?

## Database and query behavior

- Are filters, joins, and aggregations pushed into SQL where appropriate?
- Does the change avoid ORM-style analytical access patterns?
- Is the scan scope narrower than or equal to what the slice needs?

## Readability versus performance

- Is the fast path still understandable?
- Are non-obvious performance choices documented briefly?
- Did the author avoid hiding cost behind abstractions?

## Failure patterns

- Python loops over analytical rows without clear reason
- repeated serialization or conversion churn
- clever but opaque code with no measurable justification
- performance claims that are not reflected in the implementation shape

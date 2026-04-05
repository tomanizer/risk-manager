# CODE-X1: Vectorized Deterministic Service Example

## Purpose

This example shows the implementation shape the repository prefers for numerical deterministic logic.

## Preferred shape

- read validated inputs at the boundary
- convert the hot path to `numpy` arrays if the workload is dense and numerical
- perform vectorized operations rather than row-wise Python loops
- return typed outputs or typed intermediate objects only at the boundary

## Why this is good

- the hot path is obvious
- performance characteristics are easier to reason about
- correctness is easier to test against fixtures
- there is no unnecessary framework or indirection

## What to avoid

- looping over rows of dictionaries for dense numerical transforms
- hiding vectorized operations behind multiple wrapper layers
- adding classes whose only purpose is to forward to `numpy`

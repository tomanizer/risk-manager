# Test Strategy For Deterministic Services

## Purpose

This document defines what good tests look like for coding-agent work in this repository.

## Test for behavior, not volume

Tests should prove the slice is correct, not merely increase file count.

## What good tests should cover

- normal cases
- edge cases
- degraded cases
- explicit failure cases
- replay-sensitive behavior where relevant
- scope and contract fidelity

## Useful test patterns

- fixture-driven tests for deterministic services
- contract validation tests
- SQL/data-shape tests for local analytical flows
- regression tests for previously found defects

## Performance-sensitive testing

Performance itself does not need heavy benchmark theater in every PR.

But performance-sensitive slices should still test:

- that vectorized paths and SQL paths produce the right answers
- that degraded behavior does not force slow fallback paths silently
- that large-shape logic is not accidentally rewritten into row-by-row behavior

## Anti-patterns

- tests that only mirror implementation line by line
- giant snapshot tests with no clear behavior value
- meaningless mocks around deterministic local logic
- performance claims with no correctness protection

# ADR-002: Replay And Snapshot Model

## Status

Accepted

## Date

2026-04-05

## Context

Replayability is a first-class repository rule. Deterministic outputs must be reproducible from the same inputs, snapshots, versions, and workflow state.

## Decision

All governed deterministic outputs must support explicit replay context using pinned identifiers and version metadata.

At minimum, replay-aware outputs or retrieval flows should carry or be traceable to:

- snapshot identifier where relevant
- service or workflow version
- data version where relevant
- request context sufficient to re-run deterministically

No replay-sensitive flow may silently fall back to latest-available behavior once a pinned replay path is requested.

## Consequences

### Positive

- deterministic behavior can be checked in tests
- governance outputs stay auditable
- review agents can detect replay regressions

### Negative

- more metadata must be propagated through contracts
- fixture design must be more disciplined

## Alternatives considered

### Best-effort replay without pinned snapshots

Rejected because it is too easy for outputs to drift over time.

### Replay only at orchestrator level

Rejected because deterministic services themselves must also be reproducible.

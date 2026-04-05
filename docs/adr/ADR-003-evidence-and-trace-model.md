# ADR-003: Evidence And Trace Model

## Status

Accepted

## Date

2026-04-05

## Context

The repository treats evidence and replayability as first-class requirements, but there is not yet a canonical shared decision for how evidence and trace metadata should be represented.

## Decision

The platform will model evidence and trace as structured typed objects, not as incidental prose fields.

Shared contracts should provide explicit patterns for:

- evidence references
- trace or correlation context
- version metadata
- links between outputs and their supporting facts

Walkers and orchestrators may add interpretation on top of evidence, but they must not replace structured evidence references with free-form unsupported narrative.

## Consequences

### Positive

- caveats and findings can point to stable supporting artifacts
- reviewers can check evidence propagation explicitly
- downstream governance outputs remain auditable

### Negative

- contracts become more detailed early
- some output objects will carry additional metadata fields

## Alternatives considered

### Narrative-only evidence descriptions

Rejected because they are hard to validate and replay.

### Logging-only traceability

Rejected because evidence must travel with governed outputs, not only runtime logs.

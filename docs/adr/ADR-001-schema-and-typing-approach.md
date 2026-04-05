# ADR-001: Schema And Typing Approach

## Status

Accepted

## Date

2026-04-05

## Context

The repository needs one consistent way to define typed contracts across shared objects, deterministic services, walkers, orchestrators, fixtures, and replay tests.

Without a repo-level choice, agents will improvise incompatible schema patterns in different areas.

## Decision

The repository will use one canonical typed-schema approach per implementation language and will treat those schemas as the source of truth for:

- enums
- request and response objects
- replay metadata
- evidence references
- degraded and error states

For Python-based backend implementation, the initial default should be explicit typed models with validation support rather than loose dictionaries.

## Consequences

### Positive

- downstream contracts remain explicit
- validation behavior is testable
- review can focus on schema fidelity
- fixtures and replay tests can validate against the same contracts

### Negative

- early implementation must pay the cost of explicit models
- quick ad hoc prototyping becomes less convenient

## Alternatives considered

### Loose dictionaries plus documentation

Rejected because it is too easy for agents to drift on field names, nullability, and status semantics.

### Per-module schema choice

Rejected because it invites incompatible contracts across modules and workflows.

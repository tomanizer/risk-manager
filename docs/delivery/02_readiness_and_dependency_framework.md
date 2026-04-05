# Readiness And Dependency Framework

## Purpose

This document sharpens the PM agent's judgment beyond the mechanical checklist in `work_items/READY_CRITERIA.md`.

## Readiness means more than "a work item exists"

Work is ready only when a competent coding agent can implement the slice without inventing:

- missing contracts
- missing state semantics
- missing file boundaries
- missing test intent
- missing replay or evidence meaning

## Dependency closure

A dependency is closed only when one of the following is true:

- the upstream implementation is already merged
- the upstream doc or ADR canon is merged and stable enough to code against
- the dependent slice is explicitly designed to include the upstream dependency inside the same bounded PR

Dependencies are not closed merely because a draft exists or because the PM agent can imagine how the gap should be solved.

## Common block patterns

The PM agent should block work when:

- PRD and work item differ materially
- the work item requires domain inference that belongs in spec work
- status behavior is under-specified
- target files are too vague
- review expectations are not concrete
- one slice is trying to perform both foundation work and service behavior
- a review-finding fix would silently widen scope

## Target-area rule

The PM agent should not hand work to coding until the intended write area is explicit enough that a reviewer can say whether the PR stayed in bounds.

Acceptable examples:

- one named module file plus its tests
- one contracts package plus its fixtures and tests
- one deterministic service file plus its local helpers and tests

Weak examples:

- "the analytics module"
- "backend work"
- "service layer"

## Test-clarity rule

The PM agent should be able to name the expected test shape before coding starts.

Examples:

- unit tests for status transitions
- fixture-driven tests for scope fidelity
- replay tests deferred explicitly to a later work item

If the PM agent cannot say what the tests need to prove, the slice is not ready.

## Dependency questions the PM agent should ask

1. Is the upstream dependency merged, or only discussed?
2. Is the meaning of the dependency explicit enough to code against?
3. Would a failed assumption here create contract drift?
4. Can the dependency be deferred safely?
5. If deferred, is that deferral written down explicitly?

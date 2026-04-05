# Ready Criteria

## Purpose

This checklist defines when a work item is ready for autonomous implementation by a coding agent.

The PM agent should treat this document as a hard gate. If a work item fails any blocking criterion, it should be moved to `blocked/` or routed to PRD, ADR, or spec work rather than assigned for coding.

## Blocking readiness checks

Every work item in `work_items/ready/` must have all of the following:

### 1. Linked contract

- linked PRD is named explicitly
- linked PRD exists in the repository
- linked PRD status is stable enough for implementation

### 2. Scope clarity

- purpose is explicit
- in-scope work is explicit
- out-of-scope work is explicit
- the change fits one bounded implementation outcome

### 3. Dependency clarity

- blocking dependencies are listed
- those dependencies are already complete or otherwise approved as stable
- the work item does not rely on unresolved upstream contracts

### 4. Target location clarity

- intended package or file area is known
- component boundary is known:
  - `src/shared/`
  - `src/modules/`
  - `src/walkers/`
  - `src/orchestrators/`
  - `docs/`
  - `tests/`
  - `fixtures/`

### 5. Acceptance clarity

- acceptance criteria are explicit
- review focus is explicit
- the PM agent can tell when the work is done without guesswork

### 6. Test clarity

- expected test type is known:
  - unit
  - integration
  - replay
  - documentation-only with manual review
- degraded and edge-case expectations are listed where relevant

### 7. Evidence and replay clarity

For any work item that affects deterministic services, walkers, orchestrators, or governance outputs:

- evidence expectations are explicit
- replay implications are explicit
- snapshot and version semantics are not left implicit

### 8. Decision closure

- no unresolved cross-cutting architecture question remains
- any needed ADR already exists or is explicitly linked as a prerequisite

## Automatic block conditions

The PM agent must not assign a work item for coding if any of the following are true:

- linked PRD is missing
- linked PRD and work item conflict materially
- an ADR is required but missing
- target package is unknown
- acceptance criteria are too vague to review
- tests cannot be inferred safely
- the item mixes architecture design and routine implementation in one step
- the item widens scope beyond the approved PRD

## Promotion rule

A work item should move into `work_items/ready/` only when all blocking readiness checks pass.

## Completion rule

A work item should move out of `ready/` only when one of the following is true:

- it has been assigned for implementation and moved to `in_progress/`
- it has been blocked by a newly discovered dependency and moved to `blocked/`
- it has been superseded or split into narrower items

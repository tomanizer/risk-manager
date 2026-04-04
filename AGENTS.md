# AGENTS.md

This repository uses AI agents for PRD authoring, issue decomposition, implementation, review, and project coordination.

## Architecture hierarchy
1. `docs/` contains the governed architecture canon.
2. `docs/prds/` and `docs/prd_exemplars/` define implementation contracts.
3. `work_items/` holds bounded execution slices.
4. `src/` contains implementation.
5. `tests/` and `fixtures/` verify correctness and replayability.

## Agent roles

### PRD Author
- writes bounded implementation-ready PRDs
- uses the correct PRD template variant
- keeps scope narrow
- makes ambiguities explicit in Open Questions

### Coding Agent
- implements one bounded work item at a time
- stays within linked PRD and issue scope
- preserves architecture boundaries
- includes tests and required evidence/logging hooks

### Review Agent
- reviews against PRD and issue, not personal style preference
- checks contract fidelity, boundary discipline, degraded-case handling, evidence, replayability, and tests
- flags scope creep explicitly

### PM / Coordination Agent
- manages sequencing, dependency readiness, blockers, and milestone integrity
- does not redesign architecture during execution

## Non-negotiable repository rules
- deterministic services own calculations and canonical state
- walkers interpret typed outputs only
- orchestrators execute workflow state, routing, gates, and handoff only
- UI must not hide caveats or recompute canonical logic
- trust before interpretation
- challenge before governance output
- evidence and replayability are first-class requirements

## Preferred behavior
- choose the narrower implementation when ambiguous
- preserve explicit caveats rather than guessing
- prefer small, reviewable changes over broad refactors
- keep generated prose precise and low-fluff

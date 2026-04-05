# AGENTS.md

This repository uses AI agents for PRD authoring, issue decomposition, implementation, review, and project coordination.

## Architecture hierarchy
1. `docs/` contains the governed architecture canon.
2. `docs/prds/` and `docs/prd_exemplars/` define implementation contracts.
3. `prompts/` contains AI-mediated delivery instructions.
4. `work_items/` holds bounded execution slices.
5. `src/` contains implementation.
6. `tests/` and `fixtures/` verify correctness and replayability.

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

## Role separation rule

The repository uses a gated relay, not a single do-everything agent.

The intended handoff is:
1. PM / Coordination Agent
2. Issue Planner or PRD Author when needed
3. Coding Agent
4. Review Agent
5. Human merge decision

Do not collapse planning, coding, review, and merge judgment into one agent pass when operating autonomously.

Repo-visible role-specific instructions live in:
- `prompts/agents/`
- `docs/guides/overnight_agent_runbook.md`

## Freshness and branching rule

Before any PM, coding, or review pass:

1. git fetch origin
2. git switch main
3. git pull --ff-only origin main

For reviews, then checkout the latest PR head. For coding, create a fresh branch from main.

New implementation work must start from the latest `main`.

Each bounded implementation slice should use a fresh branch created from current `main`.

Agents must not continue from stale local state when canon, PR state, or linked contracts may have changed.

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

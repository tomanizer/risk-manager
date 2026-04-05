# Coding Agent Instruction

## Mission

Implement one bounded work item faithfully, deterministically, and with tests.

The coding agent is an implementation worker, not a product strategist and not an architecture owner.

## Required reading order

Before writing code, read in this order:

1. assigned work item
2. linked PRD
3. linked ADRs
4. relevant module, workflow, or prompt documentation
5. local package README files where relevant

## Primary responsibilities

- implement only the assigned slice
- preserve contract fidelity
- keep degraded states explicit
- add or update tests with the change
- preserve replayability and evidence behavior where applicable
- leave clear notes when ambiguity remains

## Operating rules

### Stay inside scope

Do not widen scope because adjacent work looks convenient.

### Prefer deterministic implementations

If the work belongs in a deterministic service, do not introduce AI behavior or fuzzy logic.

### Respect typed contracts

Do not rename fields, relax status semantics, or collapse explicit states for convenience.

### Preserve boundaries

- modules own deterministic truth
- walkers own typed interpretation
- orchestrators own workflow state, routing, and gates
- UI owns presentation only

### Make degraded behavior explicit

Missing, partial, blocked, or degraded states must surface clearly in code and tests.

### Add tests with the change

Every meaningful implementation change should include the relevant unit, integration, replay, or fixture coverage expected by the work item and PRD.

## Forbidden behavior

- architecture redesign without an ADR
- hidden fallback behavior
- silent contract drift
- speculative abstractions unrelated to the assigned slice
- unrelated refactors
- mixing multiple work items into one change without explicit PM approval

# Phased Implementation Roadmap

> Note on numbering: the PRD ID prefix, the roadmap phase number, and the containing folder name are different tracking schemes. `PRD-1.1` does not mean "Phase 1.1," and a file living under a phase-numbered folder does not redefine its roadmap phase.

## Delivery principles

- implement in vertical slices
- freeze contracts before broad downstream build
- deterministic services before walkers
- walkers before orchestrators
- challenge and replay support built in, not bolted on

## PM tracking status

As of 2026-04-07:

- Phase 1 (`PRD-1.1`) is marked phase-complete for PM sequencing purposes.
- PM should not create additional `WI-1.1.x` items in `work_items/ready/` as residual completion work.
- Next PM action is to move to the next governed phase or PRD in sequence and perform a fresh readiness assessment there.
- Any future expansion in this capability area should be treated as a new PRD or later-phase enhancement, not as remaining `PRD-1.1` completion scope.

## Planned phases

### Phase 0
Delivery foundation, shared schemas, trace, replay, config, and fixture framework.

### Phase 1
Risk Analytics core MVP.

### Phase 2
FRTB / PLA Controls and Controls & Production Integrity MVP.

### Phase 3
Limits, Approvals, and Desk Status MVP.

### Phase 4
Specialist Walkers MVP.

### Phase 5
Orchestrator MVPs.

### Phase 6
Model registry and governance depth.

### Phase 7
Human workflow and UX layer.

### Phase 8
Hardening, evaluation, and scale.

## Delivery model

PRDs are written first, then decomposed into bounded work items, then implemented by coding agents, reviewed by review agents, and sequenced by a PM / coordination agent.

# Phased Implementation Roadmap

## Delivery principles

- implement in vertical slices
- freeze contracts before broad downstream build
- deterministic services before walkers
- walkers before orchestrators
- challenge and replay support built in, not bolted on

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

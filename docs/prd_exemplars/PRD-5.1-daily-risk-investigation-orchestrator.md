# PRD-5.1: Daily Risk Investigation Orchestrator

## Variant
Orchestrator PRD

## Purpose
Run the daily workflow that selects, routes, synthesizes, challenges, and hands off material daily targets.

## In scope
- daily run trigger
- readiness gate
- target selection
- walker routing
- synthesis
- challenge gate
- governance handoff
- state persistence

## Out of scope
- breach approval lifecycle
- monthly committee pack
- UI rendering
- raw calculations

## Core run stages
1. Intake
2. Readiness gate
3. Target selection
4. Target routing
5. Investigation
6. Synthesis
7. Challenge
8. Handoff
9. Persist

## Core state
- run_id
- as_of_date
- readiness_state
- selected_targets
- target_results
- challenge_results
- handoff_status

## Core rules
1. Data Controller Walker is mandatory for selected material targets.
2. Mandatory triggers can override normal thresholds.
3. Trust caveats must propagate to handoff outputs.
4. Blocking challenge findings must prevent target handoff unless explicitly unresolved and escalated.

## Acceptance criteria
- workflow triggers correctly
- selected targets are traceable
- routing and challenge gates work
- run state is persisted and replayable

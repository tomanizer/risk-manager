# Source Layout

## Shared
`src/shared/` for schemas, trace, config, workflow state types, and utilities.

## Modules
`src/modules/` for deterministic capability modules.

## Walkers
`src/walkers/` for specialist agent wrappers and typed outputs.

## Orchestrators
`src/orchestrators/` for workflow state, routing, gates, challenge, and handoff logic.

Keep module, walker, and orchestrator responsibilities separate.

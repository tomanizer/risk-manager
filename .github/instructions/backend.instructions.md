---
applyTo: "src/**/*.py,tests/**/*.py,fixtures/**/*.py"
---

# Backend and workflow instructions

Focus on deterministic correctness and boundary discipline.

## Rules
- Module code owns calculations, deterministic services, canonical state, and workflow state.
- Walker code owns typed interpretation only.
- Orchestrator code owns workflow transitions, routing, gating, and handoff only.
- Preserve typed schemas and explicit enums.
- Preserve evidence references, snapshot/version metadata, and replayability hooks.
- Prefer explicit code over clever abstractions.

## Review checks
- Are degraded cases explicit?
- Are error states typed?
- Are tests covering positive, negative, edge, and replay cases?
- Has any hidden logic drifted across boundaries?
- Has any direct data access bypassed approved service layers?

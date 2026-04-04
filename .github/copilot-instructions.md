# Copilot Repository Instructions

This repository contains a governed architecture canon and an AI-mediated delivery system for a market risk platform.

## Always preserve these boundaries
- Deterministic services in `src/modules/` own calculations, rule execution, workflow state, and canonical truth.
- Walkers in `src/walkers/` interpret typed outputs and emit structured findings. They do not own raw calculations or approval logic.
- Orchestrators in `src/orchestrators/` execute workflows, routing, gates, challenge, and handoff. They do not hide canonical calculations.
- UI and presentation code must not recompute business logic or suppress caveats.

## Review priorities
When reviewing code or proposing changes, prioritize:
1. contract fidelity to PRD and schemas
2. architecture boundary discipline
3. degraded-case and error handling
4. evidence, traceability, and replayability
5. test coverage for positive, negative, edge, and replay cases

## Repository doctrine
- deterministic core, agentic edge
- evidence-first
- replayable outputs
- typed interfaces only
- KISS and YAGNI
- trust before interpretation
- challenge before governance output

## Do not do these things
- do not introduce raw or ad hoc data access from walkers or UI
- do not embed policy decisions in frontend code
- do not silently widen scope beyond the linked PRD or work item
- do not remove caveat, trust-state, or evidence fields for convenience
- do not refactor across module / walker / orchestrator boundaries unless explicitly requested

## When context is ambiguous
Choose the narrower implementation, preserve explicit caveats, and surface the ambiguity rather than guessing.

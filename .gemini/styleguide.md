# risk-manager review style guide

## Purpose
This repository contains a governed architecture canon and an AI-mediated implementation system for a market risk platform.

Gemini reviews should prioritize architecture fidelity, control integrity, and review usefulness over stylistic nitpicking.

## Review priorities
1. Correctness of implementation against the linked PRD or work item.
2. Preservation of module, walker, orchestrator, and UI boundaries.
3. Explicit degraded-case and error handling.
4. Preservation of evidence, trust-state, caveat, and replayability requirements.
5. Test quality, especially negative, edge, and replay cases.

## Architecture rules
- Deterministic modules own calculations, workflow state, and canonical truth.
- Walkers interpret typed outputs and emit structured findings.
- Orchestrators manage workflow state, routing, gates, challenge, and handoff.
- UI must not recompute business logic or suppress caveats.

## Review guidance
- Prefer comments that identify contract mismatch, hidden assumptions, or boundary drift.
- Do not recommend broad refactors unless there is a real architecture or correctness problem.
- Flag missing tests or weak degraded-case handling.
- Flag silent removal of metadata, evidence references, or explicit state fields.

## Avoid low-value review noise
- avoid minor naming suggestions unless they affect clarity materially
- avoid style-only comments when correctness or boundary discipline is more important
- avoid pushing extra abstractions that are not required by the PRD

# PM-X2: Implementation Brief Example

## Purpose

This example shows the shape of a strong PM handoff to a coding agent.

## Example brief

Build only the deterministic history-retrieval slice for the risk-summary service. Add `get_risk_history` in `src/modules/risk_analytics/service.py` using the existing contracts, fixture loader, and business-day resolver. Enforce inclusive `start_date` and `end_date`, explicit anchor-snapshot semantics, ascending ordered points, exact scope-aware node resolution, and the approved status behavior for missing snapshot, missing node, missing history, partial history, and degraded history. Add unit tests for request validation, anchor-snapshot validation, ordering, scope fidelity, sparse history, degraded rows, and `require_complete=true` upgrades. Do not implement summary, delta, rolling statistics, replay-suite expansion, or new evidence fields. Halt and escalate if the code would need to invent canon not present in the work item, PRD, or ADRs.

## Why this is good

- one bounded outcome
- explicit target area
- named behaviors
- named tests
- explicit out-of-scope reminders
- useful stop conditions

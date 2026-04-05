# PM-X1: Ready Versus Blocked Assessment Example

## Purpose

This example shows the expected difference between a weak PM assessment and a useful one.

## Weak blocked assessment

`BLOCKED because details are still unclear.`

This is not useful. It does not identify whether the problem is contracts, target area, tests, replay semantics, or dependency closure.

## Strong blocked assessment

`BLOCKED`

What changed since last assessment:

- foundation dependencies are now merged, so the remaining problem is contract readiness rather than missing prerequisite implementation

Scope of the next PR:

- implement `get_risk_history` only once the slice is ready

Dependencies confirmed:

- foundation contracts, fixtures, and business-day resolver are merged

Target area:

- `src/modules/risk_analytics/service.py`
- `src/modules/risk_analytics/__init__.py`
- `tests/unit/modules/risk_analytics/`

Explicit out-of-scope reminders:

- summary, delta, rolling statistics, replay-suite work

Reason:

- the work item requires the coding agent to choose what `snapshot_id` means for a multi-date history request
- history-specific status semantics are not explicit
- replay-test scope is unclear

Implementation brief:

- no coding brief should be issued until the PRD and work item define request shape, status behavior, and replay-test scope explicitly

Stop conditions:

- halt if `snapshot_id` semantics remain ambiguous
- halt if implementation would require new replay or evidence fields not named in canon

## Weak ready assessment

`READY. Implement the history service and add tests.`

This is too vague. It does not define the approved slice or the stop conditions.

## Strong ready assessment

`READY`

What changed since last assessment:

- the PRD and work item now define anchor-snapshot semantics, history-specific statuses, and test scope explicitly

Scope of the next PR:

- implement `get_risk_history` only

Dependencies confirmed:

- risk-analytics foundation contracts are merged
- deterministic fixtures and business-day resolver are merged

Target area:

- `src/modules/risk_analytics/service.py`
- `src/modules/risk_analytics/__init__.py` only if export wiring is required
- `tests/unit/modules/risk_analytics/`

Explicit out-of-scope reminders:

- summary, delta, rolling statistics, replay-suite work

Implementation brief:

- build only the deterministic history-retrieval slice for the risk-summary service. Add `get_risk_history` in `src/modules/risk_analytics/service.py` using the existing contracts, fixture loader, and business-day resolver. Enforce inclusive range semantics, explicit anchor-snapshot behavior, ascending ordered points, exact scope-aware node resolution, and the approved status behavior. Add unit tests for request validation, anchor-snapshot validation, ordering, scope fidelity, sparse history, degraded rows, and `require_complete=true` upgrades.

Stop conditions:

- halt if `snapshot_id` semantics in the PRD and work item do not match
- halt if implementation requires new replay or evidence fields not named in canon

# PM-X1: Ready Versus Blocked Assessment Example

## Purpose

This example shows the expected difference between a weak PM assessment and a useful one.

## Weak blocked assessment

`BLOCKED because details are still unclear.`

This is not useful. It does not identify whether the problem is contracts, target area, tests, replay semantics, or dependency closure.

## Strong blocked assessment

`BLOCKED`

Reason:

- the work item requires the coding agent to choose what `snapshot_id` means for a multi-date history request
- history-specific status semantics are not explicit
- the target service file is not named
- replay-test scope is unclear

Required follow-up:

- update the PRD and work item with explicit request shape and status behavior
- define the target service module
- state whether replay tests are in scope now or deferred

## Weak ready assessment

`READY. Implement the history service and add tests.`

This is too vague. It does not define the approved slice or the stop conditions.

## Strong ready assessment

`READY`

Scope:

- implement `get_risk_history` only
- write to `src/modules/risk_analytics/service.py`
- update `src/modules/risk_analytics/__init__.py` only if needed
- add unit tests in `tests/unit/modules/risk_analytics/`

Out of scope:

- summary, delta, rolling statistics, replay-suite work

Stop conditions:

- halt if `snapshot_id` semantics in the PRD and work item do not match
- halt if implementation requires new replay or evidence fields not named in canon

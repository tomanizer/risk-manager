# WI-5.1.4

## Status

**DONE** — Merged to `main` via [PR #177](https://github.com/tomanizer/risk-manager/pull/177). Replay/determinism tests for the public `start_daily_run` entrypoint are on `main`.

## Blocker

- None. Work complete.

## Linked PRD

docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md

Replay and snapshot model: [ADR-002](docs/adr/ADR-002-replay-and-snapshot-model.md).

## Linked ADRs

- ADR-002

## Linked shared infra

- `docs/shared_infra/index.md`

## Purpose

Residual replay/determinism slice for the Daily Risk Investigation Orchestrator: close the remaining gap at the public `start_daily_run` entrypoint now that telemetry has landed on `main`.

Current state on `main`:

- pinned `run_id` regression coverage already exists in [tests/unit/orchestrators/daily_risk_investigation/test_contracts.py](tests/unit/orchestrators/daily_risk_investigation/test_contracts.py)
- `generated_at` determinism helper coverage already exists in [tests/unit/orchestrators/daily_risk_investigation/test_generated_at.py](tests/unit/orchestrators/daily_risk_investigation/test_generated_at.py)
- telemetry is already included in the implementation and covered separately by [tests/unit/orchestrators/daily_risk_investigation/test_telemetry.py](tests/unit/orchestrators/daily_risk_investigation/test_telemetry.py)

The missing replay guard was an end-to-end equality assertion over the full `DailyRunResult` returned by `start_daily_run`; PR #177 closed it.

## Completion evidence on `main`

- [tests/unit/orchestrators/daily_risk_investigation/test_replay_determinism.py](tests/unit/orchestrators/daily_risk_investigation/test_replay_determinism.py) — happy-path and `BLOCKED_READINESS` two-invocation `DailyRunResult` equality for `start_daily_run`.
- Merge: [PR #177](https://github.com/tomanizer/risk-manager/pull/177).

## Scope

Add replay tests under `tests/unit/orchestrators/daily_risk_investigation/` that exercise the public `start_daily_run` entrypoint with the telemetry-included implementation already on `main`.

Required cases:

1. **Happy-path two-invocation equality:** invoke `start_daily_run` twice with identical `(as_of_date, snapshot_id, candidate_targets, measure_type)` arguments and identical fixture indices; assert the returned `DailyRunResult` instances are equal under Pydantic model equality.
2. **Blocked-readiness two-invocation equality:** repeat the same equality assertion for a blocked-readiness scenario so the short-circuit path is also replay-stable.

These tests must use the existing fixture infrastructure and must not add new fixtures or alter orchestrator implementation.

## Out of scope

- Re-implementing the already-landed pinned `run_id` literal test
- Re-implementing the already-landed `_derive_generated_at` helper test matrix
- Any changes to orchestrator implementation
- New fixture files or fixture-index extensions
- Any new typed contracts, status values, or evidence shapes
- Any telemetry assertions (covered by WI-5.1.3 tests)

## Dependencies

Runtime-gated prerequisite:

- WI-5.1.3-telemetry-adoption-and-adoption-matrix-flip

Canon (not WI-gated):

- PRD-5.1
- ADR-002

## Target area

- `tests/unit/orchestrators/daily_risk_investigation/` or `tests/replay/` per repo convention (exact path per coding agent's judgment; create the replay test file alongside existing unit tests for the orchestrator)

## Acceptance criteria

1. **Happy-path replay equality** — equal inputs across two calls to `start_daily_run` produce equal `DailyRunResult` instances for a successful run; test is present and passes.
2. **Blocked-readiness replay equality** — equal inputs across two calls to `start_daily_run` produce equal `DailyRunResult` instances for a blocked-readiness run; test is present and passes.
3. Tests use only existing fixture infrastructure; no new fixtures are introduced.
4. No orchestrator implementation code changes are introduced in this WI.

## Test intent

- **Happy-path replay equality:** call `start_daily_run` twice synchronously with identical inputs using a complete-run fixture scenario; compare the two returned `DailyRunResult` objects with `==`.
- **Blocked-readiness replay equality:** repeat the same pattern for a blocked-readiness fixture scenario to ensure the short-circuit path is equally deterministic.
- These tests should rely on the existing `run_id` and `generated_at` coverage already present on `main`; this WI closes the public-entrypoint replay gap rather than duplicating helper-level tests.

## Review focus

- Replay equality is asserted at the public `start_daily_run` boundary, not only at helper level.
- The selected scenarios are fixture-backed and deterministic on `main`.
- The tests do not duplicate telemetry assertions or helper-only `run_id` / `generated_at` logic already covered elsewhere.
- No new fixture files or orchestrator implementation changes are introduced.

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

1. **Linked contract** — PRD-5.1 and ADR-002 are merged on `main` and linked above.
2. **Scope clarity** — Residual replay-equality tests only; no implementation changes.
3. **Dependency clarity** — WI-5.1.3 is merged; full orchestrator (including telemetry) is stable on `main`.
4. **Target location** — `tests/unit/orchestrators/daily_risk_investigation/` or `tests/replay/` per repo convention.
5. **Acceptance clarity** — The remaining public-entrypoint replay assertions are named and have explicit pass/fail criteria.
6. **Test clarity** — Test types: unit/replay. Determinism assertions only; no new fixture extensions.
7. **Evidence / replay** — Existing `run_id` and `generated_at` helper-level evidence is already on `main`; this WI closes the orchestrator-entrypoint replay equality gap.
8. **Decision closure** — No unresolved replay-design decisions remain; the scope is now purely residual verification.
9. **Shared infra** — No shared infra changes; adoption matrix already updated by WI-5.1.3.

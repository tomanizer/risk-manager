# WI-5.1.2

## Status

**READY** — WI-5.1.1 merged on `main` (PR #169, commit `f02be6c`); typed contracts (`DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, `HandoffStatus`, `TerminalRunStatus`, `ReadinessState`, `OutcomeKind`), `_derive_run_id`, `orchestrator_version` constant, and `start_daily_run` stub are stable on `main`. Routed to `work_items/in_progress/` by PM.

## Blocker

- None. PM has assigned this slice to Coding Agent.

## Linked PRD

docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md

Upstream services consumed: [PRD-1.1-v2](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md) (`get_risk_summary`), [PRD-2.1](docs/prds/phase-2/PRD-2.1-controls-production-integrity-assessment-service.md) (`IntegrityAssessment`). Upstream walker: [PRD-4.1](docs/prds/phase-2/PRD-4.1-data-controller-walker-v1.md) (`assess_integrity`).

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Second coding slice for the Daily Risk Investigation Orchestrator: implement all nine stages (intake through persist) in `start_daily_run`, including the readiness gate, target selection (`MISSING_NODE` filter), routing (constant: `data_controller`), per-target investigation, synthesis, challenge gate, handoff assembly, terminal-state derivation, and `generated_at` determinism. Unit and integration tests per PRD-5.1 "Test intent". No telemetry in this slice.

## Scope

- Implement Stages 1–9 within `start_daily_run` per PRD-5.1 workflow stage definitions:
  - **Stage 1 (`intake`):** typed input validation (`ValueError` on empty `snapshot_id`, empty `candidate_targets`, `None` `snapshot_id`), `run_id` allocation via the derivation from WI-5.1.1, `started_at` monotonic clock anchor
  - **Stage 2 (`readiness_gate`):** call `get_risk_summary` for the first candidate as canary; apply exactly: `MISSING_SNAPSHOT`/`UNSUPPORTED_MEASURE` → `readiness_state = BLOCKED` with matching reason code; `MISSING_NODE` → `readiness_state = READY` with `readiness_reason_codes = ("READINESS_CANARY_MISSING_NODE",)`; success (any `RiskSummary`) → `readiness_state = READY`, empty reason codes
  - **Stage 3 (`target_selection`):** pass-through with `MISSING_NODE` exclusion filter; `RuntimeError("readiness invariant violated after gate passed")` on any other `ServiceError` from `get_risk_summary` after gate passed
  - **Stage 4 (`target_routing`):** constant routing decision (route every selected target to `data_controller.assess_integrity`); recorded internally only
  - **Stage 5 (`investigation`):** sequential `data_controller.assess_integrity` call per selected target in `selected_targets` order; `ValueError` from walker escapes unchanged; `ServiceError` captured as per-target outcome
  - **Stage 6 (`synthesis`):** structural collation of per-target outcomes into `TargetInvestigationResult` tuple; `outcome_kind` set to `ASSESSMENT` or `SERVICE_ERROR`; upstream typed object propagated by reference unchanged
  - **Stage 7 (`challenge`):** per-target gate applying the six-rule precedence from PRD-5.1 "Challenge gate" in order; `blocking_reason_codes` and `cautionary_reason_codes` propagated from upstream `IntegrityAssessment` unchanged
  - **Stage 8 (`handoff`):** structural assembly of `TargetHandoffEntry` tuple; no I/O or filtering
  - **Stage 9 (`persist`):** compute `terminal_status` per the five-level precedence from PRD-5.1 "Terminal states"; compute `degraded` (true iff any `assessment_status == DEGRADED`); compute `partial` (true iff at least one `ServiceError` and at least one `IntegrityAssessment`); compute `generated_at` as max of per-target `IntegrityAssessment.generated_at` when any assessment is present, else `datetime.combine(as_of_date, time(hour=18, minute=0, tzinfo=timezone.utc))`; construct and return frozen `DailyRunResult`
- `BLOCKED_READINESS` short-circuit: Stages 3–8 skipped when `readiness_state == BLOCKED`; `selected_targets`, `target_results`, `handoff` all set to empty tuples
- Unit tests: typed contract construction, input validation (`ValueError`), stage-ordering (instrumented via injected fakes), challenge gate truth-table covering all documented `(outcome_kind, trust_state, assessment_status)` combinations, terminal-status precedence covering all five transitions
- Integration tests using existing `controls_integrity` and `risk_analytics` fixture indices: happy path (`terminal_status == COMPLETED` or `COMPLETED_WITH_CAVEATS`), `MISSING_NODE` exclusion in selection, `HOLD_INVESTIGATION_FAILED` propagation, `BLOCKED_READINESS` short-circuit

## Out of scope

- Telemetry emission (`emit_operation` calls) — WI-5.1.3
- Adoption matrix flip — WI-5.1.3
- Replay determinism test set — WI-5.1.4
- Direct import of `get_integrity_assessment` from `controls_integrity` — **forbidden**; the orchestrator must consume `IntegrityAssessment | ServiceError` only via `data_controller.assess_integrity`
- Materiality logic, second walker, scoring, ranking, threshold logic
- Durable persistence backend, parallel execution, automatic retries
- Human-in-the-loop challenge, governance approval, UI surface
- Any new canonical trust semantics, evidence shape, or status vocabulary not in PRD-5.1

## Dependencies

Blocking:

- WI-5.1.1-orchestrator-skeleton-and-typed-contracts

Merged prerequisites:

- WI-4.1.2-data-controller-walker-delegate-slice (PRD-4.1 implementation, provides `assess_integrity`)
- WI-2.1.3-integrity-assessment-service (PRD-2.1 implementation)
- WI-1.1.4-risk-summary-core-service (PRD-1.1-v2 implementation, provides `get_risk_summary`)

Canon (not WI-gated):

- PRD-5.1
- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Target area

- `src/orchestrators/daily_risk_investigation/` (stage implementation within existing package from WI-5.1.1)
- `tests/unit/orchestrators/daily_risk_investigation/` (unit tests: challenge gate, terminal-status, stage ordering, input validation)
- `tests/integration/orchestrators/` (integration tests: happy path, degraded paths, blocked readiness)

## Acceptance criteria

### Functional

- `start_daily_run` returns a `DailyRunResult` for every well-formed input set
- All nine stages execute in fixed order; Stages 3–8 are skipped when `readiness_state == BLOCKED`
- Per-target challenge gate produces the documented `handoff_status` for every `(outcome_kind, trust_state, assessment_status)` combination reachable via existing fixtures
- Terminal-status precedence is enforced in the order documented in PRD-5.1 (highest first: `BLOCKED_READINESS`, `FAILED_ALL_TARGETS`, `COMPLETED_WITH_FAILURES`, `COMPLETED_WITH_CAVEATS`, `COMPLETED`)
- `readiness_state` and `readiness_reason_codes` are populated exactly per the readiness rules; readiness canary `MISSING_NODE` does not block the run
- `generated_at` equals max `IntegrityAssessment.generated_at` across selected targets when at least one assessment is present; falls back to `datetime.combine(as_of_date, time(hour=18, minute=0, tzinfo=timezone.utc))` when no assessment is present

### Contract

- `IntegrityAssessment` and `ServiceError` are propagated unchanged into `TargetInvestigationResult`
- `blocking_reason_codes` and `cautionary_reason_codes` in `TargetHandoffEntry` are byte-for-byte equal to the upstream tuples when an assessment is present
- No orchestrator-originated reason codes appear in any `TargetHandoffEntry`
- `snapshot_id` is mandatory; `start_daily_run` raises `ValueError` for empty or `None` `snapshot_id`

### Architecture

- Orchestrator imports `IntegrityAssessment | ServiceError` only via `src.walkers.data_controller.assess_integrity` — no direct import of `get_integrity_assessment` from `controls_integrity`
- Orchestrator imports `get_risk_summary` only from the public `src.modules.risk_analytics` surface
- No imports from `agent_runtime`; no telemetry calls (deferred to WI-5.1.3)
- No parallel execution, threading, or asyncio

### Test

- Unit tests: input validation (`ValueError`), challenge gate truth-table, terminal-status precedence, `BLOCKED_READINESS` skip behavior
- Integration tests: happy path, `MISSING_NODE` exclusion, `HOLD_INVESTIGATION_FAILED`, `BLOCKED_READINESS`
- All tests use existing fixture infrastructure; no new fixture files required

## Test intent

**Unit:**

- **Input validation:** `ValueError` raised for empty `candidate_targets`, empty `snapshot_id`, `None` `snapshot_id`
- **Challenge gate truth-table:** parametrized over all documented `(outcome_kind, trust_state, assessment_status)` combinations; assert expected `handoff_status` per PRD-5.1 precedence rules
- **Terminal-status precedence:** construct `DailyRunResult` scenarios corresponding to each terminal status; assert first-match precedence
- **Stage ordering / `BLOCKED_READINESS` skip:** inject fake upstream calls; assert Stages 3–8 produce empty tuples and no upstream calls are made when readiness is `BLOCKED`

**Integration (using existing fixture indices):**

- **Happy path:** small candidate set from existing fixture index → `terminal_status` in `{COMPLETED, COMPLETED_WITH_CAVEATS}`
- **`MISSING_NODE` path:** candidate set includes a node not in the fixture snapshot → that node excluded from `selected_targets`; run completes with remaining targets
- **`HOLD_INVESTIGATION_FAILED` path:** walker returns `ServiceError` for a target → `handoff_status == HOLD_INVESTIGATION_FAILED` for that target
- **`BLOCKED_READINESS` path:** canary target triggers `MISSING_SNAPSHOT` → `terminal_status == BLOCKED_READINESS`, `selected_targets == ()`, `target_results == ()`, `handoff == ()`

## Review focus

- Architecture boundary: no `get_integrity_assessment` direct import; only `data_controller.assess_integrity`
- Challenge gate reads only `trust_state`, `assessment_status`, and `ServiceError.status_code` per PRD-5.1 — no other upstream fields consulted for status assignment
- `IntegrityAssessment` and `ServiceError` propagated unchanged into `TargetInvestigationResult`
- `generated_at` determinism rule implemented correctly (max of assessments; fallback anchor)
- `BLOCKED_READINESS` short-circuit fully implemented; no Stages 3–8 work in blocked path
- No telemetry calls in this slice

## Suggested agent

Coding Agent (after WI-5.1.1 unblocks)

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

*Gate cleared (WI-5.1.1 merged on `main`); all must hold:*

1. **Linked contract** — PRD-5.1 is merged on `main` and linked above.
2. **Scope clarity** — Stage 1–9 implementation only; telemetry and replay tests are separate WIs.
3. **Dependency clarity** — WI-5.1.1 merged on `main` (PR #169); all upstream walker and service contracts stable.
4. **Target location** — `src/orchestrators/daily_risk_investigation/`, `tests/unit/orchestrators/`, `tests/integration/orchestrators/`.
5. **Acceptance clarity** — Functional/Contract/Architecture/Test criteria are explicit and directly derived from PRD-5.1.
6. **Test clarity** — Unit (challenge gate, terminal-status, stage-ordering, input validation) + integration (four named paths) are explicit.
7. **Evidence / replay** — No new evidence shape; `IntegrityAssessment` propagated unchanged per ADR-003. Replay determinism tests are deferred to WI-5.1.4.
8. **Decision closure** — No unresolved architecture decisions; all gate rules, status precedence, and degraded handling are normative in PRD-5.1.
9. **Shared infra** — Telemetry explicitly out of scope for this slice; adoption matrix update deferred to WI-5.1.3.

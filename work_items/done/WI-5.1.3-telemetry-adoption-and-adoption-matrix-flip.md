# WI-5.1.3

## Status

**BLOCKED** — gated on WI-5.1.2 (stage execution end-to-end) merging on `main`.

## Blocker

- WI-5.1.2-stage-execution-end-to-end must be merged and the full orchestrator stage implementation must be stable on `main` before telemetry calls are added.

**Owner:** Coding Agent completes WI-5.1.2 → human merge → PM moves this WI to `in_progress`.

## Linked PRD

docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md

Telemetry contract: [docs/shared_infra/telemetry.md](docs/shared_infra/telemetry.md). Adoption matrix: [docs/shared_infra/adoption_matrix.md](docs/shared_infra/adoption_matrix.md).

## Linked ADRs

- ADR-001
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/telemetry.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Third coding slice for the Daily Risk Investigation Orchestrator: add `emit_operation` calls for every required telemetry event per the PRD-5.1 telemetry table, assert payload discipline (no `IntegrityAssessment` payloads in logs, no `agent_runtime` import), add telemetry tests using the shared-infra test pattern established in `src/walkers/data_controller/`, and flip `src/orchestrators/` in `docs/shared_infra/adoption_matrix.md` from `planned` to `adopted`.

## Scope

- Add `src.shared.telemetry.emit_operation` calls at the correct stage boundaries per PRD-5.1 "Required events (v1)":
  - `daily_run.intake` — after Stage 1 completes; status: `OK`; context: `run_id`, `as_of_date`, `snapshot_id`, `measure_type`, `candidate_count`
  - `daily_run.readiness_gate` — after Stage 2 completes; status: `OK` when `readiness_state == READY`, else the `ServiceError.status_code` from the canary call (`MISSING_SNAPSHOT` or `UNSUPPORTED_MEASURE`); context: `run_id`, `as_of_date`, `snapshot_id`, `readiness_state`, `readiness_reason_codes`
  - `daily_run.target_selection` — after Stage 3 completes; status: `OK`; context: `run_id`, `candidate_count`, `selected_count`, `excluded_missing_node_count`
  - `daily_run.investigation` — after Stage 5 completes; status: `OK`; context: `run_id`, `selected_count`, `assessment_count`, `service_error_count`
  - `daily_run.challenge` — after Stage 7 completes; status: `OK`; context: `run_id`, `ready_for_handoff_count`, `proceed_with_caveat_count`, `hold_blocking_trust_count`, `hold_unresolved_trust_count`, `hold_investigation_failed_count`
  - `daily_run.handoff` — after Stage 8 completes; status: `OK`; context: `run_id`, `handoff_count`
  - `daily_run_complete` — at end of Stage 9; status: mapped canonical status per normative mapping (`COMPLETED` → `OK`; `COMPLETED_WITH_CAVEATS` → `DEGRADED`; `COMPLETED_WITH_FAILURES` → `PARTIAL`; `FAILED_ALL_TARGETS` → `DEGRADED`; `BLOCKED_READINESS` → `DEGRADED`); context: `run_id`, `as_of_date`, `snapshot_id`, `terminal_status`, `degraded`, `partial`, `selected_count`, `assessment_count`, `service_error_count`
- `BLOCKED_READINESS` path: emit only `daily_run.intake`, `daily_run.readiness_gate`, and `daily_run_complete`; no Stage 3–8 events
- Telemetry tests (caplog-style, following the pattern from `src/walkers/data_controller/` and `src/modules/controls_integrity/`):
  - Each required event is emitted exactly once per happy-path run with the documented context fields
  - No `IntegrityAssessment` or `ServiceError` objects appear in log payloads (low-cardinality identifiers and counts only)
  - `agent_runtime` is not imported transitively from the orchestrator package
  - `BLOCKED_READINESS` path emits exactly three events: `daily_run.intake`, `daily_run.readiness_gate`, `daily_run_complete`
- Update `docs/shared_infra/adoption_matrix.md`: flip `src/orchestrators/` row from `planned` to `adopted`; set Notes to: "Telemetry uses `src.shared.telemetry.emit_operation`; daily-run operation-log slice is WI-5.1.3; no module-local duplicate status mapping"

## Out of scope

- Any new telemetry status strings beyond those already in `_INFO_STATUSES` or `_WARNING_STATUSES` in `src.shared.telemetry.operation_log`
- Module-local status mapping in the orchestrator (status-to-level mapping is owned entirely by shared telemetry)
- Separate telemetry events for `target_routing`, `synthesis`, or `persist` stages (forbidden without a PRD update)
- `include_trace_context=True` (deferred to a future WI per PRD-5.1 open questions)
- Replay determinism tests — WI-5.1.4
- Any orchestrator stage logic changes (locked in WI-5.1.1 and WI-5.1.2)
- Any new typed contracts, status values, or evidence shapes

## Dependencies

Blocking:

- WI-5.1.2-stage-execution-end-to-end

Canon (not WI-gated):

- PRD-5.1
- ADR-001
- ADR-003
- `docs/shared_infra/telemetry.md`

## Target area

- `src/orchestrators/daily_risk_investigation/` (add `emit_operation` calls to existing implementation from WI-5.1.2)
- `docs/shared_infra/adoption_matrix.md` (flip `src/orchestrators/` row to `adopted`)
- `tests/unit/orchestrators/daily_risk_investigation/` (telemetry tests)

## Acceptance criteria

### Telemetry

- All seven events from the PRD-5.1 telemetry table are emitted exactly once per complete run (happy path)
- Each event includes exactly the context fields listed in PRD-5.1; no `IntegrityAssessment` or `ServiceError` objects appear in log payloads; only low-cardinality identifiers, counts, and canonical statuses
- `daily_run_complete` `status` field is the mapped canonical status (e.g. `OK` for `COMPLETED`), not the raw `terminal_status` enum value; `terminal_status` appears only as a context field
- `daily_run.readiness_gate` `status` is `OK` when `readiness_state == READY`; otherwise the `ServiceError.status_code` from the canary call (`MISSING_SNAPSHOT` or `UNSUPPORTED_MEASURE`)
- `BLOCKED_READINESS` path: exactly three events emitted (`daily_run.intake`, `daily_run.readiness_gate`, `daily_run_complete`); no Stage 3–8 events
- All `status` values passed to `emit_operation` are members of the canonical sets already in shared telemetry; no new status strings introduced in the orchestrator
- No `agent_runtime` import in the orchestrator package (transitively)

### Adoption matrix

- `src/orchestrators/` row in `docs/shared_infra/adoption_matrix.md` reflects `adopted`
- Notes field states: telemetry uses `src.shared.telemetry.emit_operation`; daily-run operation-log slice is WI-5.1.3; no module-local duplicate status mapping

### Test

- caplog assertion that each event is emitted exactly once per happy-path run with correct `operation` and context fields
- Assertion that no `IntegrityAssessment` or `ServiceError` payload appears in any log record across a run
- Import-hygiene assertion: `agent_runtime` is not importable transitively from `src.orchestrators.daily_risk_investigation`
- `BLOCKED_READINESS` path test: assert exactly three events emitted with correct `operation` names

## Test intent

Mirror the test pattern from `src/walkers/data_controller/` telemetry tests:

- Capture log records via pytest `caplog` or equivalent
- Assert `operation` and `status` fields on each captured record match the normative table
- Assert context fields match the documented minimums per event
- Assert no forbidden payload fields (no full typed objects)
- Assert event count per run is exactly the expected count (7 for complete run; 3 for `BLOCKED_READINESS`)

## Review focus

- Telemetry payload discipline: no full typed objects in log records; low-cardinality identifiers and counts only
- Status mapping correctness: the raw `terminal_status` enum value must not be the canonical `status` field on `daily_run_complete`; it must appear only as a context field
- `BLOCKED_READINESS` path emits exactly the three required events and no others
- `daily_run.readiness_gate` status reflects the canary `ServiceError.status_code` correctly in the blocked case
- Adoption matrix row correctly flipped to `adopted` with accurate notes
- No new status strings introduced in the orchestrator
- No stage logic changes introduced in this WI

## Suggested agent

Coding Agent (after WI-5.1.2 unblocks)

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

*Blocked until WI-5.1.2 completes; when unblocked, all must hold:*

1. **Linked contract** — PRD-5.1 and shared-infra telemetry canon are merged on `main` and linked above.
2. **Scope clarity** — `emit_operation` calls + telemetry tests + adoption matrix flip only; no stage-behavior changes.
3. **Dependency clarity** — WI-5.1.2 merged; shared telemetry contract stable on `main`.
4. **Target location** — `src/orchestrators/daily_risk_investigation/`, `docs/shared_infra/adoption_matrix.md`, `tests/unit/orchestrators/daily_risk_investigation/`.
5. **Acceptance clarity** — All telemetry event table rows are explicit; payload discipline requirements are explicit; adoption matrix update is explicit and normative in PRD-5.1.
6. **Test clarity** — caplog-style tests per established pattern; specific assertions named above.
7. **Evidence / replay** — No new evidence shape. Telemetry payloads must not include raw typed evidence objects per ADR-003 payload discipline.
8. **Decision closure** — Status mapping is normative in PRD-5.1 "Required events (v1)"; no unresolved telemetry design decisions.
9. **Shared infra** — This WI is the telemetry adoption slice; `docs/shared_infra/telemetry.md` and `docs/shared_infra/adoption_matrix.md` are both linked and explicitly modified by this WI.

# WI-4.2.6

## Status

**BLOCKED** - gated on WI-4.2.5 (interpretive logic) merging on `main`.

## Blocker

- Quant Walker v2 must first return `QuantInterpretation` on `main` so telemetry can be wired against the settled public output and status mapping.

**Owner:** Coding Agent completes WI-4.2.5 -> human merge -> PM moves this WI to `ready/`.

## Linked PRD

`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md`

Sibling telemetry pattern on `main`: `src/walkers/data_controller/walker.py`. Shared telemetry canon: `docs/shared_infra/telemetry.md`.

## Linked ADRs

- ADR-001
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/telemetry.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Adopt the shared telemetry contract for Quant Walker v2 by emitting one structured operation event per `summarize_change` invocation and updating the `src/walkers/` adoption-matrix notes to include Quant coverage.

## Scope

- Update `src/walkers/quant/walker.py` to:
  - capture `start_time` via `timer_start()` before the upstream call
  - emit exactly one `emit_operation("summarize_change", ...)` event at function exit
  - map `status` to `ServiceError.status_code` on error paths and to `risk_change_profile.status.value` on `QuantInterpretation` paths
  - include `node_ref`, `measure_type`, `as_of_date`, and `snapshot_id` in payload context
  - include `change_kind`, `significance`, and `confidence` on `QuantInterpretation` paths and explicit `None` for those keys on `ServiceError` paths
- Add telemetry tests for success and error paths.
- Update the `src/walkers/` row note in `docs/shared_infra/adoption_matrix.md` so it records both `data_controller` and `quant` walker coverage.

## Out of scope

- Any change to inference rules or contract fields
- Replay-determinism test suite
- New status strings or module-local status-to-log-level mapping
- Orchestrator telemetry or any `agent_runtime` coupling
- New fixtures or upstream service behavior changes

## Dependencies

Blocking:

- WI-4.2.5-quant-walker-v2-interpretive-logic

Canon (not WI-gated):

- ADR-001
- ADR-003
- `docs/shared_infra/telemetry.md`

## Target area

- `src/walkers/quant/walker.py`
- `tests/unit/walkers/quant/`
- `docs/shared_infra/adoption_matrix.md`

## Acceptance criteria

- Every `summarize_change` invocation emits exactly one structured `operation` event.
- The emitted `operation` value is exactly `"summarize_change"`.
- `status` equals `ServiceError.status_code` on error paths and `risk_change_profile.status.value` on `QuantInterpretation` paths.
- `change_kind`, `significance`, and `confidence` are present and populated on `QuantInterpretation` paths.
- `change_kind`, `significance`, and `confidence` are present with explicit `None` values on `ServiceError` paths.
- No trace-context keys are emitted when `include_trace_context=False`.
- `docs/shared_infra/adoption_matrix.md` records Quant Walker telemetry coverage in the `src/walkers/` row notes while keeping the row status aligned with shared canon.
- The walker uses `src.shared.telemetry.emit_operation` directly and does not duplicate status-to-level mapping logic.
- Caplog-based tests prove exactly one event is emitted for a representative success path and a representative `ServiceError` path.

## Test intent

- Mirror the `data_controller` walker telemetry pattern: configure operation logging, invoke `summarize_change`, capture the structured payload, and assert operation name, status, context fields, and conditional quant fields.
- Add an autouse fixture to reset shared operation logging defaults around each quant telemetry test.
- Verify payload discipline by asserting no extra narrative or full typed-object payload is logged.

## Review focus

- Exact PRD status mapping and one-event-per-call behavior
- Payload discipline and explicit-`None` conditional field handling
- Adoption-matrix note update without unrelated shared-infra edits

## Suggested agent

Coding Agent (after unblock)

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

*Blocked until WI-4.2.5 completes; when unblocked, all must hold:*

1. **Linked contract** - PRD-4.2-v2 is merged and WI-4.2.5 has landed the public `QuantInterpretation` behavior on `main`.
2. **Scope clarity** - Telemetry wiring, telemetry tests, and adoption-matrix note update only.
3. **Dependency clarity** - Interpretive logic is already stable; shared telemetry contract is already canonical.
4. **Target location** - `src/walkers/quant/`, quant walker telemetry tests, and `docs/shared_infra/adoption_matrix.md` are explicit.
5. **Acceptance clarity** - Event count, payload fields, and status mapping are concrete and reviewable.
6. **Test clarity** - caplog-style tests and logging reset behavior are explicit.
7. **Evidence / replay** - Telemetry must not create a parallel evidence surface or log full typed payloads.
8. **Decision closure** - PRD-4.2-v2 and shared telemetry canon close the needed event semantics.
9. **Shared infra** - This slice explicitly adopts shared telemetry and updates the adoption matrix accordingly.

## Residual notes for PM / downstream

- Keep this slice separate from replay tests so review can focus on logging behavior and adoption evidence.
- WI-4.2.7 stays blocked until this telemetry-adopted implementation is the public `main` baseline.

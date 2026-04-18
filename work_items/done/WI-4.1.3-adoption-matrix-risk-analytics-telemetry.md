# WI-4.1.3

## Linked PRD

PRD-4.1-data-controller-walker-v1 (context only; this slice is shared-infra documentation alignment)

## Linked canon

- `docs/shared_infra/adoption_matrix.md` — target file to update
- `docs/shared_infra/telemetry.md`
- `docs/shared_infra/index.md`

## Linked ADRs (informational)

- ADR-002-replay-and-snapshot-model.md (no change)
- ADR-003-evidence-and-trace-model.md (no change)

## Purpose

Remove documented drift: `docs/shared_infra/adoption_matrix.md` lists `src/modules/risk_analytics/` telemetry as `planned`, but `src/modules/risk_analytics/service.py` already emits structured operation events via `src.shared.telemetry.emit_operation` per completed **WI-1.1.11**. Reconcile the matrix row only—no code changes.

## Scope

- Update the **`src/modules/risk_analytics/`** row in **`docs/shared_infra/adoption_matrix.md`**:
  - Set **Status** to **`adopted`** (direct use of shared telemetry contract / `emit_operation`).
  - Replace **Notes** with a short factual reference: telemetry uses `src/shared/telemetry` and the risk analytics operation-log slice is WI-1.1.11 (no module-local duplicate status mapping).
- Do not edit `src/`, `tests/`, or other docs for this WI.

## Out of scope

- Any change to `src/shared/telemetry/` behavior or APIs
- Any change to `src/modules/risk_analytics/service.py` or tests
- Updating the `src/walkers/` or `src/orchestrators/` rows (covered by WI-4.1.4 and WI-4.1.5 respectively)
- PRD-4.1 text edits (optional follow-up; not required for matrix reconciliation)

## Dependencies

- WI-1.1.11 (done) — establishes `risk_analytics` → `src.shared.telemetry` adoption

## Target area

- `docs/shared_infra/adoption_matrix.md` only

## Acceptance criteria

- `risk_analytics` telemetry row reflects **`adopted`** with notes consistent with existing code (`emit_operation` via shared telemetry, WI-1.1.11).
- No other matrix rows are changed in this WI.
- Review can verify against `src/modules/risk_analytics/service.py` imports and `emit_operation` usage.

## Test intent

- Documentation-only slice: manual review against `READY_CRITERIA.md` and grep/spot-check of `emit_operation` in `service.py`.

## Suggested agent

Human operator or Coding Agent (single-file doc edit only—no application code).

## Review focus

- Matrix status matches in-repo usage (`adopted` not `planned`).
- Notes do not claim helpers that do not exist; do not reintroduce superseded “shared outcome emission helper” wording.

## Stop conditions

- Stop if review finds `risk_analytics` telemetry is not actually wired to `src.shared.telemetry` on current `main` (escalate to PM / drift monitor).
- Stop if a broader doc refactor is requested—this WI is a single-row fix only.

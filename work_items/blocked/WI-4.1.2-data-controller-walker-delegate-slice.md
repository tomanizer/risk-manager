# WI-4.1.2

## Status

**BLOCKED** — gated on acceptance of WI-4.1.1 (implementation PRD on `main`).

## Blocker

- The WI-4.1.1 deliverable PRD file under docs/prds/phase-2/ (expected name PRD-4.1-data-controller-walker-v1.md unless WI-4.1.1 chooses another filename) must be merged and treated as stable implementation contract.

**Owner:** PRD / Spec Author completes WI-4.1.1 → human merge → PM moves this WI to `ready/`.

## Linked PRD

- **WI-4.1.1 deliverable:** PRD-4.1-data-controller-walker-v1.md under docs/prds/phase-2/ (exact filename finalized when WI-4.1.1 lands)
- PRD-2.1 (`docs/prds/phase-2/PRD-2.1-controls-production-integrity-assessment-service.md`) — service semantics unchanged

## Linked ADRs

- ADR-002
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

First **coding** slice for Data Controller Walker: a **thin** implementation in a new **data_controller** package under `src/walkers/` (package path is created by this WI; do not cite the full path in backticks until it exists) that delegates **only** to the public `controls_integrity` service API (`get_integrity_assessment`), returning the same typed `IntegrityAssessment | ServiceError` union, with unit tests proving **parity** versus calling the service directly under identical fixture/index inputs.

## Scope

- Add the **data_controller** package under `src/walkers/` (module layout consistent with repo patterns) exposing a single clear entry point (name per WI-4.1.1 PRD — e.g. a function or small façade) that:
  - Calls **only** the public API `get_integrity_assessment` from `controls_integrity` (or package export path defined in PRD-4.1 v1).
  - Does **not** duplicate trust aggregation, check ordering, reason-code logic, or evidence validation (all remain in `src/modules/controls_integrity`).
  - Passes through fixture indices / parameters exactly as the service expects (no hidden defaults beyond what the service documents).
- Unit tests that assert **byte-for-byte or model-equal** parity: for a representative matrix of inputs (success + representative `ServiceError` paths), walker output equals direct `get_integrity_assessment` output.
- Package `__init__` / exports as appropriate for a walker root per existing `src/walkers/README.md` intent.

## Out of scope

- Changing PRD-2.1 or service behavior
- Trust logic in the walker (any interpretation beyond pass-through)
- `TrustAssessment`, `supporting_findings`, `recommended_next_step`, or other exemplar-only constructs not mandated by WI-4.1.1 PRD
- Orchestrators, UI, telemetry wiring
- Replay harness changes unless PRD-4.1 v1 explicitly requires (default: no)

## Dependencies

- **WI-4.1.1** — implementation PRD merged (blocking)
- WI-2.1.3 — merged
- WI-2.1.6 — merged
- PRD-2.1, ADR-002, ADR-003

## Target area

- New package **data_controller** under `src/walkers/`
- Matching unit tests under tests/unit/walkers/ (e.g. a data_controller test package created alongside implementation; exact layout per repo convention)

## Acceptance criteria

- Walker entry point returns **`IntegrityAssessment | ServiceError`** only (same types as `get_integrity_assessment`); no parallel error or “wrapper” trust type.
- No imports of private service internals (only public module API as defined in WI-4.1.1 PRD).
- Unit tests demonstrate parity vs direct service calls for all cases exercised in the test matrix (minimum: at least one full success assessment, and one case each for `MISSING_SNAPSHOT`, `MISSING_NODE`, `MISSING_CONTROL_CONTEXT` if reachable with existing fixtures, or the maximal subset the PRD allows without inventing fixtures).
- Lint/typecheck clean; no new non-deterministic behavior.

## Test intent

- Parametrized or table-driven tests: same args → walker vs service → equal results (`==` on models or structured dict equivalence per existing test patterns).

## Review focus

- Boundary discipline: walker is a façade, not a second trust engine
- Import hygiene: public API only
- Test sufficiency for parity claim

## Suggested agent

Coding Agent (after unblock)

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

*Blocked until WI-4.1.1 completes; when unblocked, all must hold:*

1. **Linked contract** — WI-4.1.1 PRD exists on `main` and is linked at top of this file (update path if filename differs).
2. **Scope clarity** — Pass-through + parity tests only.
3. **Dependency clarity** — WI-4.1.1 merged; service and contracts stable.
4. **Target location** — data_controller package under `src/walkers/`, tests under tests/unit/walkers/ per convention.
5. **Acceptance clarity** — Parity and typed union criteria above.
6. **Test clarity** — Unit tests, parity matrix explicit in PRD/WI.
7. **Evidence / replay** — No change to replay artifacts unless PRD requires; walker adds no new snapshot semantics.
8. **Decision closure** — Walker behavior fully specified by WI-4.1.1 PRD + PRD-2.1.
9. **Shared infra** — None required for this slice unless PRD mandates telemetry row in adoption matrix (default: no matrix update).

## Residual notes for PM / downstream

After WI-4.1.2 merges, consider telemetry/adoption matrix row for `src/walkers/` when a separate WI introduces walker telemetry.

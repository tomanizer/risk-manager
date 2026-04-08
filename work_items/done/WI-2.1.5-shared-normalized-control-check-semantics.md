# WI-2.1.5

## Linked PRD

PRD-2.1

## Linked ADRs

- ADR-002

## Purpose

Eliminate duplicate PASS / WARN / FAIL / UNKNOWN semantics for `reason_codes` and `evidence_refs` between `ControlCheckResult` (contracts) and the controls-integrity fixture loader (`_validate_normalized_row_semantics`), per Copilot review on PR #145. One canonical implementation should enforce the same invariants for normalized rows and per-check results so contract and fixtures cannot drift.

## Scope

- introduce a **single shared validation helper** in `src/modules/controls_integrity/contracts/` (same module as `ControlCheckResult` and `NormalizedControlRecord`, reusing existing `_deduplicated_sorted_reason_codes` where appropriate)
- refactor `ControlCheckResult.validate_result` to delegate invariant checks to that helper (preserve existing validation outcomes and error intent; message text may be unified only if behavior stays equivalent)
- extend `NormalizedControlRecord` so **construction-time validation** enforces:
  - deduplicated, lexicographically ascending `reason_codes` (mirror the `ControlCheckResult` `mode="before"` normalization pattern where it applies)
  - the same PASS / WARN / FAIL / UNKNOWN + `reason_codes` + `evidence_refs` rules currently enforced in the fixture loader
- remove `_validate_normalized_row_semantics` and `_sorted_reason_codes` from `src/modules/controls_integrity/fixtures/loader.py`; rely on `NormalizedControlRecord` validation when building pack rows (fixture snapshot validators should not re-implement the same rules)
- add or extend **unit tests** under `tests/unit/modules/controls_integrity/` that assert invalid `NormalizedControlRecord` payloads fail validation with clear errors (cover at least one case per state class: PASS with codes/refs, WARN/FAIL without refs, UNKNOWN without refs and without `CHECK_RESULT_MISSING`, unsorted / duplicate reason codes if normalization is not applied to that field)
- re-export surface: only if needed for tests or callers; prefer keeping the helper **internal** (`_` prefix) unless PRD or existing package patterns require a public API

## Out of scope

- `get_integrity_assessment` / WI-2.1.3 service logic beyond what falls out from stricter `NormalizedControlRecord` validation
- changes to JSON fixture files or fixture pack schema (unless a record becomes invalid once contracts tighten — then fix fixtures only as required to remain honest)
- repo-wide extraction of `EvidenceRef` (ADR-003 follow-ups)
- walkers, orchestrators, UI
- broad refactors of `IntegrityAssessment` or trust aggregation

## Dependencies

- WI-2.1.1-controls-integrity-contracts-and-enums
- WI-2.1.2-controls-integrity-fixtures-and-index

Note: WI-2.1.2 must be merged to `main` before starting this slice (implementation removes loader-only validators introduced there).

## Target Area

- `src/modules/controls_integrity/contracts/models.py` (or a small sibling module under `contracts/` if the team prefers splitting; stay within the contracts package boundary)
- `src/modules/controls_integrity/fixtures/loader.py`
- `tests/unit/modules/controls_integrity/`

## Acceptance Criteria

- there is exactly **one** implementation of the PASS / WARN / FAIL / UNKNOWN + `reason_codes` + `evidence_refs` invariant rules used by both `ControlCheckResult` and `NormalizedControlRecord`
- `NormalizedControlRecord` rejects invalid combinations at model validation time (no reliance on the fixture loader alone for those rules)
- fixture loader no longer contains parallel `_validate_normalized_row_semantics` / `_sorted_reason_codes` logic; existing fixture-pack and index tests remain green
- `ControlCheckResult` behavior remains aligned with PRD-2.1 check semantics (no relaxation of WARN/FAIL evidence requirements, UNKNOWN / `CHECK_RESULT_MISSING` pairing, or PASS emptiness rules)
- no new non-deterministic or wall-clock-dependent validation

## Test Intent

- contract-focused unit tests for invalid `NormalizedControlRecord` instances
- full existing `controls_integrity` unit suite passes (regression)

## Why This Unblocks Downstream Work

WI-2.1.3 and later consumers can treat `NormalizedControlRecord` as self-enforcing the same per-check semantics already modeled on `ControlCheckResult`, reducing the risk of inconsistent trust inputs from fixtures versus live assembly paths.

## Residual Blocker / Escalation

None after WI-2.1.2 is on `main`. If tightening `NormalizedControlRecord` breaks an existing fixture JSON row, update the fixture to remain PRD-honest rather than weakening validation.

## Suggested Agent

Coding Agent

## Review Focus

- semantic parity with pre-change `ControlCheckResult.validate_result` and prior fixture loader rules
- boundary discipline: contracts own cross-field invariants; loader owns pack/index structure only
- no scope creep into service or walker layers

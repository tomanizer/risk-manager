# WI-2.1.6

## Linked PRD

PRD-2.1 (EvidenceRef schema and validation rules; gap closure in “Reuse and gap analysis” / “Open questions”)

## Linked ADRs

- ADR-003
- ADR-002 (replay-stable contracts; no semantic change to evidence shape)

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Close the documented cross-module gap: implement a **repo-wide shared** typed `EvidenceRef` in `src/shared/` per ADR-003, matching PRD-2.1 field names and validation rules, and migrate `controls_integrity` off the module-local class so walkers and future modules can import one canonical type without copy-paste.

## Scope

- add a small shared module at `src/shared/evidence.py` defining `EvidenceRef` with the **same** fields and invariants as today’s module-local model:
  - `evidence_type`, `evidence_id`, `source_as_of_date`, `snapshot_id`
  - non-empty `evidence_type` and `evidence_id` after strip
  - `ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)` consistent with existing patterns
- remove the duplicate class from `src/modules/controls_integrity/contracts/models.py`; import shared `EvidenceRef` there so `ControlCheckResult`, `NormalizedControlRecord`, and service code keep working unchanged at the **semantic** level (JSON/schema equivalence for existing fixtures and replay artifacts)
- re-export `EvidenceRef` from `src/modules/controls_integrity/contracts/__init__.py` and package `__init__.py` as today (import from shared under the hood) unless review prefers direct shared imports only — prefer minimal public API churn for callers
- export `EvidenceRef` from `src/shared/__init__.py` when consistent with existing `src/shared` export style
- update `docs/shared_infra/adoption_matrix.md` with a row for `src/modules/controls_integrity/` → shared evidence contract → `adopted` (or `partial` if only this module migrates in this slice; state honestly)
- add or adjust **unit tests** so shared-model validation is covered (at least the non-empty field rules); keep existing `controls_integrity` contract and replay tests green

## Out of scope

- changing PRD-2.1 evidence rules or adding new evidence fields
- migrating other modules (e.g. risk_analytics) to shared `EvidenceRef` in this slice
- Data Controller Walker, orchestrators, UI
- telemetry changes (not required for this WI)
- FRTB / PLA or any new check types

## Dependencies

- WI-2.1.1-controls-integrity-contracts-and-enums (merged)
- WI-2.1.5-shared-normalized-control-check-semantics (merged)

## Target area

- `src/shared/` (new evidence contract module + `__init__.py` exports as needed)
- `src/modules/controls_integrity/contracts/models.py`
- `src/modules/controls_integrity/contracts/__init__.py`
- `src/modules/controls_integrity/__init__.py` (only if re-exports change)
- `docs/shared_infra/adoption_matrix.md`
- `tests/unit/` (shared evidence tests and/or existing controls_integrity tests)

## Acceptance criteria

- exactly **one** authoritative `EvidenceRef` implementation lives under `src/shared/`; no duplicate definition remains under `controls_integrity/contracts`
- all existing tests for `controls_integrity` (unit + replay) pass without weakening PRD-2.1 semantics
- adoption matrix reflects this module’s use of the shared evidence contract
- no new wall-clock or non-deterministic behavior in validation

## Test intent

- unit tests for invalid `EvidenceRef` payloads on the shared model (empty type/id)
- regression: full existing `controls_integrity` test suite and any replay tests touching integrity assessments

## Review focus

- contract fidelity to PRD-2.1 `EvidenceRef` section
- boundary discipline: shared type only; trust aggregation and walker logic untouched
- import hygiene: avoid circular dependencies between `src/shared` and modules

## Suggested agent

Coding Agent

## Residual notes for PM / downstream

After this lands, **Data Controller Walker** work still needs Issue Planner / PRD alignment: `docs/prd_exemplars/PRD-4.1-data-controller-walker.md` is an exemplar and names `TrustAssessment` with fields not 1:1 with `IntegrityAssessment`; do not start walker coding until a bounded WI maps service output to walker contracts without inventing semantics.

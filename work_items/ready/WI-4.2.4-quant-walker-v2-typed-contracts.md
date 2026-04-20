# WI-4.2.4

## Status

**READY** - PRD-4.2-v2 is merged on `main`; the v1 Quant Walker package and upstream `RiskChangeProfile` contract are already stable on `main`.

## Blocker

- None. PM can assign this slice to Coding Agent.

## Linked PRD

`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md`

Existing walker package on `main`: `src/walkers/quant/`. Upstream service semantics: [`docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md).

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Create the Quant Walker v2 typed contract surface before behavior changes land: define `QuantInterpretation`, the five closed walker vocabularies, and the pinned walker-version constant so later inference and telemetry slices can build on a reviewed, stable contract.

## Scope

- Add `src/walkers/quant/contracts.py` defining:
  - `QuantInterpretation`
  - `ChangeKind`
  - `SignificanceLevel`
  - `ConfidenceLevel`
  - `QuantCaveatCode`
  - `InvestigationHint`
- Introduce the non-empty `QUANT_WALKER_VERSION` constant at the Quant Walker package boundary for v2 use.
- Update `src/walkers/quant/__init__.py` only as needed to expose the typed contract surface cleanly.
- Touch `src/walkers/quant/walker.py` only if needed to import or expose the new contract surface without changing runtime behavior.
- Add unit tests proving contract construction, enum closure, frozen-model behavior, and `extra="forbid"` enforcement.

## Out of scope

- Any change to `summarize_change` runtime behavior or return value on success
- Inference-rule implementation for `change_kind`, `significance`, `confidence`, `caveats`, or `investigation_hints`
- Telemetry adoption or adoption-matrix note changes
- Replay-determinism test suite
- New fixtures, fixture-index extensions, or upstream service changes

## Dependencies

Merged prerequisites:

- WI-4.2.3-quant-walker-v2-implementation-prd
- WI-4.2.2-quant-walker-delegate-slice
- PRD-1.1-v2 implementation already stable on `main`

Canon (not WI-gated):

- ADR-001
- ADR-002
- ADR-003

## Target area

- `src/walkers/quant/contracts.py`
- `src/walkers/quant/__init__.py`
- `src/walkers/quant/walker.py` only for narrow contract-surface wiring if required
- `tests/unit/walkers/quant/test_contracts.py`

## Acceptance criteria

- `QuantInterpretation` exists as a frozen Pydantic model with `extra="forbid"` and the exact field set named in PRD-4.2-v2: `risk_change_profile`, `change_kind`, `significance`, `confidence`, `caveats`, `investigation_hints`, `walker_version`.
- `ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode`, and `InvestigationHint` exist as closed `StrEnum` vocabularies with exactly the PRD-listed members and no extras.
- `QuantInterpretation` does not duplicate upstream replay metadata fields at the top level.
- `QUANT_WALKER_VERSION` exists, is non-empty, and is importable from the Quant Walker package surface used by later slices.
- `summarize_change` continues to return the existing v1 `RiskChangeProfile | ServiceError` union after this slice; no interpretive output is returned yet.
- Existing parity behavior remains unchanged; no telemetry call is added in this slice.
- Unit tests prove `QuantInterpretation` rejects unknown fields, preserves immutability, and accepts the typed upstream `RiskChangeProfile` field.
- Unit tests prove each enum vocabulary matches the PRD exactly.

## Test intent

- Construct a representative `RiskChangeProfile`, then instantiate `QuantInterpretation` and assert field typing, frozen behavior, and `extra="forbid"` rejection.
- Assert each enum's value set equals the PRD-listed vocabulary exactly.
- Assert `summarize_change` still behaves as the v1 delegate surface after the contract module lands.

## Review focus

- Contract fidelity to PRD-4.2-v2 field list and closed vocabularies
- Strict separation between contract introduction and behavior change
- No accidental widening of the public Quant Walker behavior in this slice

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

1. **Linked contract** - PRD-4.2-v2 is merged on `main` and linked above.
2. **Scope clarity** - Typed contracts and version constant only; no interpretive logic or telemetry.
3. **Dependency clarity** - WI-4.2.3 and WI-4.2.2 are merged; upstream `RiskChangeProfile` contract is stable.
4. **Target location** - `src/walkers/quant/` and `tests/unit/walkers/quant/` are explicit.
5. **Acceptance clarity** - Exact model fields and enum vocabularies are named and reviewable.
6. **Test clarity** - Unit tests for contract construction and enum closure are explicit.
7. **Evidence / replay** - This slice preserves upstream replay metadata as the single source of truth and introduces only the pinned walker-version anchor.
8. **Decision closure** - No unresolved contract-shape decision remains; PRD-4.2-v2 closes the vocabulary and field semantics.
9. **Shared infra** - Shared infra canon is linked; no shared-infra behavior changes occur in this slice.

## Residual notes for PM / downstream

- This is the contract-first prerequisite for every remaining Quant Walker v2 coding slice.
- WI-4.2.5 should not start until these contracts are merged on `main`.

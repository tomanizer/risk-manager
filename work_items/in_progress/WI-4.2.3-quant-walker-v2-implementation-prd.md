# WI-4.2.3

## Linked PRD

`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` (primary deliverable: author and merge the interpretive-output PRD).

Upstream service contract (read-only; must not change semantics): [`docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md) (PRD-1.1-v2).

v1 walker delegate PRD is archived on the same merge as this WI (historical text; filename PRD-4.2-quant-walker-v1-archived.md under docs/prds/phase-2/archive/). For linking, use PRD-4.2-v2 **Supersedes** and the archive copy — do not backtick the archived path here (canon-lineage execution-surface rule).

## Linked ADRs

- ADR-001 (schema and typing)
- ADR-002 (replay and snapshot model)
- ADR-003 (evidence and trace model)

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`
- `docs/shared_infra/telemetry.md`

## Purpose

Close all PRD-4.2 v1 Open Questions required for Module 1 MVP by authoring **PRD-4.2-v2: Quant Walker v2 — Interpretive Output**. This PRD defines the typed `QuantInterpretation` output shape, all classification vocabularies and deterministic inference rules, the telemetry adoption requirement, the downstream consumer contract for PRD-5.1-v2, and the issue decomposition guidance for WI-4.2.4 → WI-4.2.7.

## Scope

- New PRD file `docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` authored and merged to `main`.
- No changes to `src/` or `tests/`. This WI moves the v1 PRD into docs/prds/phase-2/archive/ as PRD-4.2-quant-walker-v1-archived.md alongside merging v2 (see PRD-4.2-v2 **Supersedes** line).

## Out of scope

- Implementation under `src/walkers/quant/` (coding slices are WI-4.2.4 → WI-4.2.7)
- Orchestrator routing, telemetry implementation, walker interpretive logic (all deferred to downstream WIs)
- Any edit to PRD-1.1-v2 service semantics

## Dependencies

- PRD-4.2-v1 and PRD-1.1-v2 are stable on `main` (not runtime-gated).
- WI-4.2.2
- Merged prerequisite detail: delegate slice on `main` (PR #168); v1 implementation exists at `src/walkers/quant/`.

## Target area

- `docs/prds/phase-2/` (new PRD file)
- `work_items/in_progress/` → moves to `work_items/done/` on merge

## Acceptance criteria

- PRD-4.2-v2 exists under `docs/prds/phase-2/`, is consistently numbered, and is implementation-ready.
- Every PRD-4.2 v1 Open Question required for Module 1 MVP is closed with a typed decision (no open inference-rule or vocabulary decisions pushed to coding).
- `QuantInterpretation` typed output shape is fully defined with field list, types, and frozen / `extra="forbid"` contract.
- `ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode`, `InvestigationHint` vocabularies are closed enums with deterministic inference rules.
- Downstream consumer contract for PRD-5.1-v2 is explicit and self-contained in the PRD.
- Telemetry requirements (event payload, status mapping, `emit_operation` invocation) are specified.
- Issue decomposition guidance covers WI-4.2.4 → WI-4.2.7 with sequencing constraints.
- Hierarchy localization and multi-function delegation are explicitly deferred with stated v3 triggers.
- PRD-1.1-v2 semantics are cross-referenced, not restated or altered.

## Test intent

Documentation-only: review agent verifies contract alignment with PRD-1.1-v2, ADR-001/002/003, walker charters, and downstream consumer contract completeness for PRD-5.1-v2.

## Review focus

- All PRD-4.2 v1 Open Questions required for MVP are closed (no deferred items left as "TBD" for coding)
- Typed contracts and inference rules are complete enough that WI-4.2.4 → WI-4.2.7 can be issued without further PRD negotiation
- Downstream consumer contract is sufficient for PRD-5.1-v2 author to begin drafting
- No PRD-1.1-v2 drift; no new ADR-level concept introduced without flagging

## Suggested agent

PRD / Spec Author

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

1. **Linked contract** — Delivers PRD-4.2-v2 file under `docs/prds/phase-2/`; links PRD-1.1-v2 as upstream service canon without altering it.
2. **Scope clarity** — PRD authoring only; explicit exclusion of implementation work.
3. **Dependency clarity** — Upstream service contract and v1 implementation stable on `main`.
4. **Target location** — `docs/prds/phase-2/`.
5. **Acceptance clarity** — Criteria above are reviewable without guesswork.
6. **Test clarity** — Doc review only; no code tests in this WI.
7. **Evidence / replay** — PRD specifies walker replay-safety requirements and `walker_version` pin.
8. **Decision closure** — No new ADR required; all vocabulary and inference-rule decisions are closed in the PRD.
9. **Shared infra** — Shared infra canon linked; telemetry adoption is specified in the PRD and deferred to WI-4.2.6 for implementation.

## Residual notes for PM / downstream

- Once this WI merges, the Issue Planner should be invoked to produce WI-4.2.4 → WI-4.2.7 from PRD-4.2-v2 §"Issue decomposition guidance".
- WI-4.2.5 is the gating slice for PRD-5.1-v2 implementation work; PRD-5.1-v2 author may draft in parallel using PRD-4.2-v2 §"Downstream consumer contract".
- Move this file to `work_items/done/` after the PR merges to `main`.

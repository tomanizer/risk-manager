# WI-4.1.1

## Linked PRD

PRD-4.1-data-controller-walker-v1 (primary deliverable: author the implementation PRD under docs/prds/phase-2/; do not use backtick-wrapped paths to not-yet-created files — reference_integrity flags them).

Upstream service contract (read-only; must not change semantics): [`docs/prds/phase-2/PRD-2.1-controls-production-integrity-assessment-service.md`](docs/prds/phase-2/PRD-2.1-controls-production-integrity-assessment-service.md) (PRD-2.1).

## Linked ADRs

- ADR-002 (replay and snapshot model)
- ADR-003 (evidence and trace model)

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Non-binding background

- `docs/prd_exemplars/PRD-4.1-data-controller-walker.md` (exemplar only; v1 PRD must **not** adopt `TrustAssessment`, `supporting_findings`, or `recommended_next_step` as normative walker output)

## Purpose

Lock **Data Controller Walker v1** to a **typed pass-through** of `get_integrity_assessment` results: `IntegrityAssessment | ServiceError`, with explicit boundaries so coding agents do not invent trust semantics or exemplar-only fields.

## Scope

- Add a new **implementation PRD** under `docs/prds/phase-2/` (filename per repo convention, e.g. PRD-4.1-data-controller-walker-v1.md) that:
  - Defines walker v1 responsibility as **delegation only** to the public `controls_integrity` API (`get_integrity_assessment` and its documented contracts).
  - States that the walker’s governed output type(s) are **the same** typed union as the service surface: success is `IntegrityAssessment`; failure paths use the existing typed `ServiceError` envelope (no parallel “walker trust” model).
  - Explicitly **rejects** normative use of exemplar-only concepts: no `TrustAssessment` aggregate as canonical output, no required `supporting_findings` or `recommended_next_step` fields for v1 unless PRD-2.1 / module contracts already provide them (they do not for the service — do not invent).
  - Cross-references PRD-2.1 for all trust-state, check, evidence, and degraded semantics; **no change** to PRD-2.1 wording or service semantics.
  - States replay/evidence expectations consistent with ADR-002 and ADR-003 (propagation of snapshot/version context as already required by the service output).
- Optionally add a one-line pointer in `docs/catalog/walkers.md` or a “Related PRD” note only if the repo’s doc style requires it for discoverability (keep diff minimal).

## Out of scope

- Any edit that changes PRD-2.1 trust or integrity semantics
- Implementation under `src/walkers/` or `src/modules/` (coding is WI-4.1.2+)
- Orchestrators, UI, telemetry adoption work
- FRTB / PLA or new check types
- Normative adoption of exemplar `TrustAssessment` / handoff narrative fields for v1

## Dependencies

Merged prerequisite work items:

- WI-2.1.3-integrity-assessment-service
- WI-2.1.6-shared-evidence-ref-extraction

PRD-2.1 is stable on main (not a WI dependency for runtime gating).

## Target area

- `docs/prds/phase-2/` (new PRD file)
- Optional: `docs/catalog/walkers.md` (discovery only, minimal)

## Acceptance criteria

- New PRD exists, is numbered/titled consistently with Phase 2 PRDs, and is implementation-ready (typed outputs, error union, no ambiguity that would force coding to invent semantics).
- Walker v1 is defined as **pass-through** of `IntegrityAssessment | ServiceError` from the public service API only.
- Exemplar-only fields (`TrustAssessment`, `supporting_findings`, `recommended_next_step`) are explicitly out of scope for v1 or deferred with **no** implied contract for the first coding slice.
- PRD-2.1 is cited as the sole source of trust/integrity semantics; no conflicting parallel definitions.
- Open Questions lists any future v2+ topics (e.g. richer walker narrative) without blocking v1 implementation.

## Test intent

- Documentation-only: review agent verifies contract alignment with PRD-2.1, ADR-002/003, and WI-4.1.2 readiness (no missing typed pass-through definition).

## Review focus

- No accidental widening into exemplar semantics
- No PRD-2.1 drift
- Clear handoff to WI-4.1.2 (walker code = thin delegate + tests)

## Suggested agent

PRD / Spec Author

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

1. **Linked contract** — Delivers new PRD file under `docs/prds/phase-2/`; links PRD-2.1 as upstream service canon without altering it.
2. **Scope clarity** — Pass-through only; explicit exclusion of exemplar-only output shapes.
3. **Dependency clarity** — Service and shared evidence work complete (WI-2.1.3, WI-2.1.6); PRD-2.1 stable.
4. **Target location** — `docs/prds/phase-2/` (+ optional catalog pointer).
5. **Acceptance clarity** — Criteria above are reviewable without guesswork.
6. **Test clarity** — Doc review + PRD/spec agent self-check; no code tests in this WI.
7. **Evidence / replay** — PRD states walker defers to service outputs that already carry replay/evidence metadata per ADR-002/003.
8. **Decision closure** — No new ADR required unless spec author discovers a cross-cutting gap (escalate to PM/human).
9. **Shared infra** — Declare if walker PRD references shared evidence types only via PRD-2.1 / `controls_integrity` exports (no new shared-infra behavior).

## Residual notes for PM / downstream

- **WI-4.1.2 remains blocked** until this PRD is accepted on `main`. After merge, promote WI-4.1.2 from `blocked/` to `ready/` (or equivalent relay step).

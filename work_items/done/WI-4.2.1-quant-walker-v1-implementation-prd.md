# WI-4.2.1

## Linked PRD

PRD-4.2-quant-walker-v1 (primary deliverable: author the implementation PRD under docs/prds/phase-2/; do not use backtick-wrapped paths to not-yet-created files — reference_integrity flags them).

Upstream service contract (read-only; must not change semantics): [`docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md) (PRD-1.1-v2).

## Linked ADRs

- ADR-001 (schema and typing)
- ADR-002 (replay and snapshot model)
- ADR-003 (evidence and trace model)

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Lock **Quant Walker v1** to a **typed pass-through** of `get_risk_change_profile` results: `RiskChangeProfile | ServiceError`, with explicit boundaries so coding agents do not invent quant interpretation semantics, wrapper outputs, or telemetry scope in v1.

## Scope

- Add a new **implementation PRD** under `docs/prds/phase-2/` (filename per repo convention, PRD-4.2-quant-walker-v1.md) that:
  - Defines walker v1 responsibility as **delegation only** to the public `risk_analytics` API (`get_risk_change_profile` and its documented contracts).
  - States that the walker's governed output type(s) are **the same** typed union as the service surface: success is `RiskChangeProfile`; failure paths use the existing typed `ServiceError` envelope (no parallel walker model).
  - Cross-references PRD-1.1-v2 for service semantics and keeps those semantics unchanged.
  - States replay/evidence expectations consistent with ADR-001, ADR-002, and ADR-003.
  - States explicit v1 deferrals for telemetry, multi-delegate expansion, narrative behavior, and orchestrator routing.

## Out of scope

- Any edit that changes PRD-1.1-v2 service semantics
- Implementation under `src/walkers/` or `tests/` (coding is WI-4.2.2)
- Orchestrators, UI, telemetry adoption work
- New types, new error envelope, or new status vocabulary

## Dependencies

PRD-1.1-v2 is stable on main (not a WI dependency for runtime gating).

## Target area

- `docs/prds/phase-2/` (new PRD file)

## Acceptance criteria

- New PRD exists, is numbered/titled consistently with Phase 2 PRDs, and is implementation-ready (typed outputs, error union, no ambiguity that would force coding to invent semantics).
- Walker v1 is defined as **pass-through** of `RiskChangeProfile | ServiceError` from the public service API only.
- Telemetry, multi-delegate expansion, narrative behavior, and orchestrator routing are explicitly out of scope for v1.
- PRD-1.1-v2 is cited as the source of quant/risk service semantics; no conflicting parallel definitions.

## Test intent

- Documentation-only: review agent verifies contract alignment with PRD-1.1-v2, ADR-001/002/003, and WI-4.2.2 readiness.

## Review focus

- No accidental widening beyond delegation-only v1 scope
- No PRD-1.1-v2 drift
- Clear handoff to WI-4.2.2 (walker code = thin delegate + parity tests)

## Suggested agent

PRD / Spec Author

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

1. **Linked contract** — Delivers PRD-4.2 file under `docs/prds/phase-2/`; links PRD-1.1-v2 as upstream service canon without altering it.
2. **Scope clarity** — Pass-through only; explicit exclusion of telemetry/narrative/multi-delegate/orchestrator v1 scope.
3. **Dependency clarity** — Upstream service contract stable on `main`.
4. **Target location** — `docs/prds/phase-2/`.
5. **Acceptance clarity** — Criteria above are reviewable without guesswork.
6. **Test clarity** — Doc review only; no code tests in this WI.
7. **Evidence / replay** — PRD states walker defers to service outputs for replay/evidence context.
8. **Decision closure** — No new ADR required for v1.
9. **Shared infra** — Shared infra canon linked; quant-walker telemetry adoption deferred from v1 by contract.

## Residual notes for PM / downstream

- PRD-4.2 is merged on `main`; WI-4.2.2 is unblocked and tracked in `work_items/ready/`.

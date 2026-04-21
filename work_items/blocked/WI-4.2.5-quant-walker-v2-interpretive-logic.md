# WI-4.2.5

## Status

**BLOCKED** - gated on WI-4.2.4 (typed contracts) merging on `main`.

## Blocker

- `QuantInterpretation` and the closed v2 walker vocabularies must exist on `main` before the behavior change lands so inference review happens against a stable typed contract.

**Owner:** Coding Agent completes WI-4.2.4 -> human merge -> PM moves this WI to `ready/`.

## Linked PRD

`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md`

Existing implementation on `main`: `src/walkers/quant/walker.py` currently delegates to the upstream service and returns `RiskChangeProfile | ServiceError`. Upstream service semantics: [`docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md).

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

Implement the Quant Walker v2 interpretive behavior: widen `summarize_change` to return `QuantInterpretation | ServiceError`, preserve upstream propagation rules, and encode every PRD-defined inference rule in a single focused behavior slice without mixing telemetry adoption.

## Scope

- Update `src/walkers/quant/walker.py` so `summarize_change`:
  - still delegates to `get_risk_change_profile` first
  - returns the upstream `ServiceError` unchanged on error paths
  - raises the same `ValueError` as the upstream service on request-validation paths
  - constructs `QuantInterpretation` on successful upstream `RiskChangeProfile` results
- Implement deterministic inference for:
  - `change_kind`
  - `significance`
  - `confidence`
  - `caveats`
  - `investigation_hints`
  - `walker_version`
- Update package exports only as needed for the widened public surface.
- Add or update unit tests covering the reachable inference-rule matrix and the v2 contract migration of the existing parity tests.

## Out of scope

- `emit_operation` telemetry wiring
- `docs/shared_infra/adoption_matrix.md` updates
- Replay-focused two-invocation equality suite
- New fixtures, new upstream service statuses, or any change to `risk_analytics` semantics
- Orchestrator wiring or PRD-5.1-v2 implementation

## Dependencies

Blocking:

- WI-4.2.4-quant-walker-v2-typed-contracts

Merged prerequisites:

- WI-4.2.3-quant-walker-v2-implementation-prd
- WI-4.2.2-quant-walker-delegate-slice
- PRD-1.1-v2 implementation already stable on `main`

Canon (not WI-gated):

- ADR-001
- ADR-002
- ADR-003

## Target area

- `src/walkers/quant/walker.py`
- `src/walkers/quant/__init__.py`
- `tests/unit/walkers/quant/`
- `tests/unit/walkers/quant/test_summarize_change_parity.py`

## Acceptance criteria

- `summarize_change` is still importable as `from src.walkers.quant import summarize_change`.
- On successful upstream calls, `summarize_change` returns `QuantInterpretation` and preserves the upstream object verbatim in `.risk_change_profile`.
- On upstream `ServiceError` results, `summarize_change` returns the same `ServiceError` unchanged.
- On request-validation failures, `summarize_change` raises the same `ValueError` message the upstream service raises.
- The public return type annotation is exactly `QuantInterpretation | ServiceError`.
- `change_kind`, `significance`, `confidence`, `caveats`, and `investigation_hints` are computed exactly per PRD-4.2-v2 inference rules using only typed upstream fields.
- `caveats` and `investigation_hints` are deduplicated and returned in lexicographic ascending order.
- No private `risk_analytics` internals are imported.
- Unit tests cover the maximal reachable rule matrix for all five interpretive outputs using existing fixtures.
- Tests explicitly cover reachable `SummaryStatus` values on `main`: `OK`, `DEGRADED`, `MISSING_COMPARE`, and `MISSING_HISTORY`.

## Test intent

- Use table-driven tests that map each reachable fixture-backed scenario to the expected `ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode` tuple, and `InvestigationHint` tuple.
- Retain explicit service-error and `ValueError` propagation assertions so the v2 widening does not regress v1 error semantics.
- Keep the test matrix reviewable: each row should be traceable back to a named PRD rule clause.

## Review focus

- Rule fidelity to PRD-4.2-v2 without hidden thresholds or new semantics
- Preservation of upstream error propagation and request-validation behavior
- Narrow slice discipline: interpretive logic only, no telemetry or adoption-matrix work mixed in

## Suggested agent

Coding Agent (after unblock)

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

*Blocked until WI-4.2.4 completes; when unblocked, all must hold:*

1. **Linked contract** - PRD-4.2-v2 and the merged WI-4.2.4 typed contracts are on `main`.
2. **Scope clarity** - Interpretive logic and rule-matrix tests only; telemetry remains out of scope.
3. **Dependency clarity** - Contract surface is stable; upstream `risk_analytics` semantics are already stable.
4. **Target location** - `src/walkers/quant/` and the specific quant walker test files are explicit.
5. **Acceptance clarity** - Success-path transformation, error propagation, and rule-coverage expectations are concrete.
6. **Test clarity** - Table-driven unit tests and parity-test migration are explicit.
7. **Evidence / replay** - Upstream replay metadata remains nested on `risk_change_profile`; no parallel evidence surface is introduced.
8. **Decision closure** - PRD-4.2-v2 fully closes the inference rules and vocabularies needed for this slice.
9. **Shared infra** - Shared infra canon is linked; telemetry adoption is explicitly deferred to WI-4.2.6.

## Residual notes for PM / downstream

- This is the gating implementation slice for PRD-5.1-v2 coding work because it makes the typed Quant Walker output exist on `main`.
- Keep telemetry adoption separated so review can focus on inference correctness first.

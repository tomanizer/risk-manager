# PRD-4.1: Data Controller Walker v1

## Header

- **PRD ID:** PRD-4.1
- **Title:** Data Controller Walker v1 — Delegation-Only Implementation
- **Phase:** Phase 2
- **Status:** Ready for implementation
- **Layer:** Walker
- **Type:** Thin typed delegate
- **Primary owner:** Technical Owner, Data Controller Walker
- **Upstream service PRD:** PRD-2.1 (Controls and Production Integrity Assessment Service)
- **Related ADRs:** ADR-002 (replay and snapshot model), ADR-003 (evidence and trace model)
- **Related components:** `src/modules/controls_integrity/` (service), `src/walkers/data_controller/` (new package, created by WI-4.1.2)
- **Exemplar (non-normative background only):** `docs/prd_exemplars/PRD-4.1-data-controller-walker.md`

## Purpose

Provide the first walker implementation for the Data Controller Walker: a thin typed delegate that calls the public `controls_integrity` service API and returns its output unchanged.

Walker v1 exists to establish the walker package, entry point, import hygiene, and parity-test pattern. It does not add trust logic, narrative generation, or interpretive semantics beyond what the deterministic service already provides.

All trust-state classification, check aggregation, false-signal-risk mapping, evidence validation, and degraded-case handling remain in `src/modules/controls_integrity/` as governed by PRD-2.1. This PRD does not restate or alter PRD-2.1 semantics.

## Why this is the v1 slice

The repository rule is: walkers interpret typed outputs from modules; they do not own canonical logic. Before a walker can add interpretive value (narrative caveats, recommended next steps, richer findings), the delegation boundary must exist and be tested.

This v1 slice establishes that boundary with the minimum viable implementation: call the service, return its result, prove parity. Richer walker behavior is a v2+ concern.

## In scope

- New `data_controller` package under `src/walkers/` with a single public entry point
- Entry point delegates exclusively to `get_integrity_assessment` from the public `controls_integrity` module API
- Walker returns the same typed union as the service: `IntegrityAssessment | ServiceError`
- No wrapper types, no semantic transformation, no additional fields
- Fixture-index parameters passed through unchanged
- Unit tests proving output parity between walker and direct service calls

## Out of scope

- Any change to PRD-2.1 service semantics, contracts, or behavior
- `TrustAssessment` as a walker output type (exemplar concept; not adopted for v1)
- `supporting_findings` as a required or optional walker output field
- `recommended_next_step` as a required or optional walker output field
- Walker-originated trust aggregation, check ordering, reason-code logic, or evidence validation
- Narrative or caveat generation by the walker
- FRTB / PLA or new check types
- Orchestrator routing, UI rendering, or governance sign-off
- Telemetry adoption for the walker layer (tracked separately per shared-infra adoption matrix)
- Replay harness changes (walker adds no new snapshot semantics; service outputs already carry replay context)
- Batch or multi-target walker invocations

## Users and consumers

Primary consumers of the walker entry point:

- Daily Risk Investigation orchestrator (future)
- Governance / Reporting Walker (future, consumes walker output for narrative)

All consumers receive the same `IntegrityAssessment | ServiceError` types that the service produces. The walker introduces no new types for consumers to handle.

## Walker contract

### Public entry point

The walker exposes a single function as its public entry point.

**Function name:** `assess_integrity`

**Location:** `src/walkers/data_controller/` package (exact module layout per repo walker conventions; exported via package `__init__.py`)

**Signature:**

```python
def assess_integrity(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    snapshot_id: str | None = None,
    *,
    risk_fixture_index: FixtureIndex | None = None,
    controls_fixture_index: ControlsIntegrityFixtureIndex | None = None,
) -> IntegrityAssessment | ServiceError:
```

**Behavior:** Calls `get_integrity_assessment` with the same arguments and returns its result unchanged.

### Import rules

The walker must import only from the public `controls_integrity` module API:

- `from src.modules.controls_integrity import get_integrity_assessment`

The walker must not import from:

- `src.modules.controls_integrity.service` directly
- `src.modules.controls_integrity.contracts` submodules directly
- Any private helper, constant, or internal function of the service

Type imports needed for the signature (`NodeRef`, `MeasureType`, `IntegrityAssessment`, `ControlsIntegrityFixtureIndex`, etc.) must use the same public export paths that the service documents:

- `from src.modules.controls_integrity import IntegrityAssessment, ControlsIntegrityFixtureIndex`
- `from src.modules.risk_analytics.contracts import NodeRef, MeasureType`
- `from src.modules.risk_analytics.fixtures import FixtureIndex`
- `from src.shared import ServiceError`

### Output type

`IntegrityAssessment | ServiceError`

This is the same typed union returned by `get_integrity_assessment`. The walker does not wrap, extend, or transform this union.

### No wrapper types

The walker must not introduce:

- A `WalkerResult`, `WalkerOutcome`, `DataControllerResult`, or similar wrapper type
- Additional fields on the return path (no `walker_metadata`, `walker_trace`, etc.)
- A parallel error type or error-code vocabulary

## Error handling

The walker propagates all error semantics from the service unchanged:

- `ServiceError` with status codes `MISSING_SNAPSHOT`, `MISSING_NODE`, `MISSING_CONTROL_CONTEXT` — returned as-is
- `RequestValidationFailure` / `ValueError` raised by the service for invalid inputs — propagated unchanged (the walker does not catch and re-wrap these)

The walker adds no new error codes, no new error types, and no fallback behavior.

## Replay and evidence

The walker adds no replay or evidence semantics of its own. All replay and evidence guarantees are satisfied by the service output, which already carries:

- `snapshot_id` — pinned snapshot context (ADR-002)
- `data_version` — data version for replay (ADR-002)
- `service_version` — service version for replay (ADR-002)
- `generated_at` — deterministic timestamp (ADR-002)
- `evidence_refs` on each `ControlCheckResult` — structured typed evidence (ADR-003)

The walker does not strip, modify, or supplement any of these fields.

## Acceptance criteria

### Functional

- Walker entry point `assess_integrity` exists and is importable from the `data_controller` walker package
- For any valid combination of inputs, `assess_integrity(args)` returns an object equal to `get_integrity_assessment(args)`
- For all three `ServiceError` paths (`MISSING_SNAPSHOT`, `MISSING_NODE`, `MISSING_CONTROL_CONTEXT`), walker output equals direct service output

### Contract

- Walker return type is `IntegrityAssessment | ServiceError` — no wrapper, no additional fields
- No imports of private service internals (only public module API)
- No new types defined in the walker package for v1

### Architecture

- Trust logic remains in `src/modules/controls_integrity/`; the walker is a facade only
- Walker package location is `src/walkers/data_controller/` per `src/walkers/README.md`

### Test

- Parametrized or table-driven unit tests demonstrate parity: same inputs produce equal outputs when called via walker vs. direct service call
- Test matrix covers at minimum: one successful `IntegrityAssessment` (all checks pass), and one case each for `MISSING_SNAPSHOT`, `MISSING_NODE`, `MISSING_CONTROL_CONTEXT`
- Tests use existing fixture infrastructure; no new fixtures required for v1

## Test intent

Tests must prove that the walker is a faithful delegate with no semantic divergence from the service.

**Pattern:** For each test case, call both `assess_integrity` (walker) and `get_integrity_assessment` (service) with identical arguments and assert equality on the result.

**Minimum parity matrix:**

| Case | Expected outcome type | Key assertion |
| --- | --- | --- |
| All checks pass | `IntegrityAssessment` | walker result == service result |
| Warning check with evidence | `IntegrityAssessment` | walker result == service result |
| Failing check | `IntegrityAssessment` | walker result == service result |
| Missing snapshot | `ServiceError` | walker result == service result |
| Missing node | `ServiceError` | walker result == service result |
| Missing control context | `ServiceError` | walker result == service result |

If existing fixtures do not cover all six cases, the coding agent should cover the maximal subset reachable with current fixtures and note any gaps.

## Issue decomposition guidance

This PRD is implemented by a single work item:

- **WI-4.1.2** — Data Controller Walker delegate slice: thin facade + parity tests

No further decomposition is needed. WI-4.1.2 is currently in `work_items/blocked/` pending acceptance of this PRD on `main`.

Sequencing:

1. This PRD (WI-4.1.1) merges first
2. WI-4.1.2 is promoted from `blocked/` to `ready/`
3. Coding agent implements WI-4.1.2
4. Review agent reviews against this PRD and WI-4.1.2 acceptance criteria

## Open questions (v2+ only — none block v1)

- **Richer walker narrative:** v2+ may add walker-specific caveats, human-readable summaries, or recommended-next-step hints. These would require new output fields or a wrapper type. Deferred until the delegation boundary is proven and orchestrator consumption patterns are clearer.
- **Telemetry adoption:** The shared-infra adoption matrix lists `src/walkers/` telemetry as `planned`. A separate WI should add telemetry when the first walker telemetry work item lands. Not required for v1.
- **Batch or multi-target invocation:** v1 is single-target only. Batch patterns are an orchestrator concern, not a walker v1 concern.
- **Exemplar alignment:** The exemplar `TrustAssessment` type in `docs/prd_exemplars/PRD-4.1-data-controller-walker.md` may inform v2+ design. It is non-normative for v1 and must not be adopted without a PRD update.

## Reviewer checklist

- Walker v1 is delegation-only; no trust logic in the walker
- Output type is `IntegrityAssessment | ServiceError` — no wrapper types
- PRD-2.1 semantics are cross-referenced, not restated or altered
- Exemplar-only fields (`TrustAssessment`, `supporting_findings`, `recommended_next_step`) are explicitly out of scope
- Import rules restrict walker to public module API only
- Acceptance criteria are sufficient for WI-4.1.2 coding without guesswork
- Replay and evidence expectations defer to service outputs per ADR-002 and ADR-003
- No FRTB / PLA or new check types have leaked in
- No backtick-wrapped references to paths that do not yet exist in work items

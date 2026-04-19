# WI-4.2.2

## Status

**DONE (draft state transition)** — verified against `origin/main` on 2026-04-19. The Quant Walker delegate slice is implemented on `main`; the remaining issue is work-item state hygiene.

## Blocker

- None. This local file is a draft to move the canonical WI from `work_items/in_progress/` to `work_items/done/`.

## Linked PRD

docs/prds/phase-2/PRD-4.2-quant-walker-v1.md

Planned walker package path for this WI is src/walkers/quant/ (plain text only until created on main). Upstream service semantics: [PRD-1.1-v2](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md).

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

First **coding** slice for Quant Walker: a **thin** implementation in `src/walkers/quant/` that delegates **only** to the public `risk_analytics` service API (`get_risk_change_profile`), returning the same typed `RiskChangeProfile | ServiceError` union, with unit tests proving **parity** versus calling the service directly under identical inputs.

## Scope

- Add the **quant** package under `src/walkers/` (module layout consistent with repo patterns) exposing one entry point `summarize_change` that:
  - Calls **only** the public API `get_risk_change_profile` from `risk_analytics`.
  - Passes through request inputs unchanged: `node_ref`, `measure_type`, `as_of_date`, `compare_to_date`, `lookback_window`, `require_complete`, `snapshot_id`, `fixture_index`.
  - Returns pass-through `RiskChangeProfile | ServiceError` with no wrapper types, no field transformation, and no additional fields.
- Package `__init__` / exports as appropriate for walker roots per existing `src/walkers/README.md` intent.
- Unit tests that assert parity matrix coverage from PRD-4.2 Test intent: walker output equals direct `get_risk_change_profile` output, including `ValueError` propagation parity.

## Completion evidence on `main`

- [src/walkers/quant/__init__.py](src/walkers/quant/__init__.py) exports `summarize_change` from the package root.
- [src/walkers/quant/walker.py](src/walkers/quant/walker.py) implements the thin delegate and returns `RiskChangeProfile | ServiceError` directly from `get_risk_change_profile`.
- [tests/unit/walkers/quant/test_summarize_change_parity.py](tests/unit/walkers/quant/test_summarize_change_parity.py) covers:
  - successful change profile parity
  - `UNSUPPORTED_MEASURE`
  - `MISSING_SNAPSHOT`
  - `MISSING_NODE`
  - invalid `lookback_window`
  - blank `snapshot_id`
  - `compare_to_date > as_of_date`

## Acceptance verification against `main`

### Functional

- `summarize_change` exists and is importable from `src.walkers.quant`.
- The delegate calls `get_risk_change_profile` with unchanged inputs and returns the direct result unchanged.
- The service-error parity rows required by the WI are present in the test matrix.
- The `ValueError` propagation rows required by the WI are present in the test matrix.

### Contract

- Return type in [walker.py](src/walkers/quant/walker.py) is exactly `RiskChangeProfile | ServiceError`.
- The walker imports only public `risk_analytics` surfaces and approved typed contract/fixture imports.
- No walker-local wrapper types or extra package surfaces were introduced.
- Signature defaults match the upstream service defaults.

### Architecture

- Quant logic remains in `src/modules/risk_analytics/`; the walker is only a facade.
- Package location and layout match the intended `src/walkers/quant/` + `__init__.py` re-export pattern.
- No orchestrator coupling, other-walker coupling, or `agent_runtime` coupling was introduced.

### Test

- The parity matrix required by the WI is implemented in one table-driven unit suite.
- Existing fixture infrastructure is reused; no new fixtures were introduced for v1.

## Correct state transition

The canonical file currently tracked on `main` is:

- [work_items/in_progress/WI-4.2.2-quant-walker-delegate-slice.md](work_items/in_progress/WI-4.2.2-quant-walker-delegate-slice.md)

Based on the implementation and tests already present on `main`, the correct transition is:

1. Move the canonical WI from `work_items/in_progress/` to `work_items/done/`.
2. Update the status from `READY` / `in_progress` wording to `DONE`.
3. Add a short completion-evidence section referencing the quant walker package and parity tests.
4. Do not reopen implementation scope; this is a bookkeeping correction, not a new coding WI.

## Suggested verification commands

- `pytest -q tests/unit/walkers/quant/test_summarize_change_parity.py`
- `ruff check src/walkers/quant tests/unit/walkers/quant`

## Out of scope

- Any walker-owned interpretive logic (hierarchy localization, significance, narrative, recommended next step, caveat synthesis)
- Multi-function delegation (`get_risk_summary`, `get_risk_delta`, `get_risk_history`) in v1
- Telemetry for Quant Walker package/component in v1
- Orchestrator coupling or routing changes (including PRD-5.1 integration)
- New fixtures or fixture-index extensions for v1
- New types, wrapper outputs, error envelopes, status vocabulary, or ADR-level semantics

## Dependencies

Merged prerequisite:

- WI-4.2.1-quant-walker-v1-implementation-prd

Canon (not WI-gated by runtime):

- PRD-4.2
- PRD-1.1-v2
- ADR-001
- ADR-002
- ADR-003

## Target area

- New package quant under `src/walkers/` (single walker module + `__init__.py` re-export)
- Matching unit tests under tests/unit/walkers/ (exact layout per repo convention)

## Acceptance criteria

### Functional

- Walker entry point `summarize_change` exists and is importable as `from src.walkers.quant import summarize_change`
- For any valid combination of inputs, `summarize_change(args)` returns an object equal (`==` on the pydantic model or its structural equivalent for `ServiceError`) to `get_risk_change_profile(args)` called with the same arguments
- For each documented `ServiceError` path (`UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`), walker output equals direct service output
- For each documented `ValueError` validation path (invalid `lookback_window`, blank `snapshot_id`, `compare_to_date > as_of_date`), the walker raises the same `ValueError` (same message) that the service raises

### Contract

- Walker return type annotation is exactly `RiskChangeProfile | ServiceError` — no wrapper, no `Optional`, no additional fields
- No imports of private service internals (only public module API and the established `contracts` / `fixtures` submodule type imports)
- No new types defined in the walker package for v1 (the package contains the entry point and its module file only; nothing else)
- Defaults on the walker signature match `get_risk_change_profile` defaults exactly

### Architecture

- Quant logic remains in `src/modules/risk_analytics/`; the walker is a facade only
- Walker package location is src/walkers/quant/ per `src/walkers/README.md`
- Package layout mirrors `src/walkers/data_controller/` (single `walker.py` module exporting one entry point via `__init__.py`)
- No coupling to PRD-5.1 orchestrator code, no coupling to any other walker, no coupling to `agent_runtime`

### Test

- Parametrized or table-driven unit tests demonstrate parity: same inputs produce equal outputs (or equal raised exceptions) when invoked via walker vs. direct service call
- Test matrix covers at minimum: one successful `RiskChangeProfile` case, plus one case each for `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`, plus at least one `ValueError` propagation case
- Tests use existing `risk_analytics` fixture infrastructure (`build_fixture_index` / passed-in `fixture_index`); no new fixture files or fixture-index extensions are required for v1
- If existing fixtures do not cover any required parity row, the coding agent must cover the maximal subset reachable with current fixtures and explicitly note any gap (deferred to a v2+ Open Question; do not invent new fixtures in v1)

## Test intent

Tests must prove that the walker is a faithful delegate with no semantic divergence from the service.

**Pattern:** For each test case, call both `summarize_change` (walker) and `get_risk_change_profile` (service) with identical arguments and assert equality on the result. For `ValueError` cases, assert that both raise `ValueError` with the same message.

**Minimum parity matrix:**

| Case | Trigger | Expected outcome | Key assertion |
| --- | --- | --- | --- |
| Successful change profile | valid `node_ref`, supported `measure_type`, `as_of_date` with snapshot, prior business day available | `RiskChangeProfile` with in-object `status` per service rules | walker result `==` service result; both objects field-equal |
| Unsupported measure | `measure_type` not in fixture pack's `supported_measures` | `ServiceError(status_code="UNSUPPORTED_MEASURE", operation="get_risk_change_profile")` | walker result `==` service result |
| Missing snapshot | `snapshot_id` does not exist (or no snapshot for `as_of_date`) | `ServiceError(status_code="MISSING_SNAPSHOT", operation="get_risk_change_profile")` | walker result `==` service result |
| Missing node | current snapshot exists but `node_ref` + `measure_type` not present in it | `ServiceError(status_code="MISSING_NODE", operation="get_risk_change_profile")` | walker result `==` service result |
| Invalid `lookback_window` | `lookback_window` set to any value other than `60` | `ValueError` from request validation | walker raises same `ValueError` as service (same message) |
| Blank `snapshot_id` | `snapshot_id=""` | `ValueError` from request validation | walker raises same `ValueError` as service (same message) |
| `compare_to_date > as_of_date` | invalid compare-date input | `ValueError` from request validation | walker raises same `ValueError` as service (same message) |

## Review focus

- Boundary discipline: walker is a facade with no quant interpretation logic
- Import hygiene: public module API plus approved typed contract imports only
- Parity-test sufficiency against PRD-4.2 matrix and `ValueError` propagation

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

1. **Linked contract** — PRD-4.2 exists on `main` and is linked at top of this file.
2. **Scope clarity** — Delegation-only `summarize_change` + parity tests only.
3. **Dependency clarity** — WI-4.2.1 merged; upstream service contract stable.
4. **Target location** — quant package under `src/walkers/`, tests under tests/unit/walkers/ per convention.
5. **Acceptance clarity** — Functional/Contract/Architecture/Test criteria are explicit and directly lifted from PRD-4.2.
6. **Test clarity** — Unit tests with explicit parity matrix and error-propagation cases.
7. **Evidence / replay** — Walker adds no replay/evidence semantics; service outputs remain source of truth.
8. **Decision closure** — No unresolved architecture decision remains for v1; ADRs linked.
9. **Shared infra** — Shared infra canon linked; Quant Walker telemetry explicitly out of scope for this v1 slice.

## Residual notes for PM / downstream

- This WI appears complete on `main`; the remaining work is PM / repo-hygiene state correction.
- Keep telemetry, multi-delegate expansion, and orchestrator routing as future WI(s) only.

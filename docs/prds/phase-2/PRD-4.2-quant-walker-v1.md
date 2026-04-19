# PRD-4.2: Quant Walker v1

## Header

- **PRD ID:** PRD-4.2
- **Title:** Quant Walker v1 — Delegation-Only Implementation
- **Phase:** Phase 2
- **Status:** Ready for implementation
- **Layer:** Walker
- **Type:** Thin typed delegate
- **Primary owner:** Technical Owner, Quant Walker
- **Upstream service PRD:** PRD-1.1-v2 (Risk Summary Service v2)
- **Sibling walker reference (pattern only, not a contract):** PRD-4.1 (Data Controller Walker v1)
- **Future consumer (not built in v1):** PRD-5.1 (Daily Risk Investigation Orchestrator) — quant walker integration is an explicit PRD-5.1 v2+ deferral
- **Related ADRs:** ADR-001 (schema and typing), ADR-002 (replay and snapshot model), ADR-003 (evidence and trace model)
- **Related shared infra:** `docs/shared_infra/index.md`, `docs/shared_infra/adoption_matrix.md`
- **Related components (existing on `main`):** `src/modules/risk_analytics/` (service), `src/modules/risk_analytics/contracts/` (typed contracts), `src/modules/risk_analytics/fixtures/` (fixture index), `src/walkers/data_controller/` (sibling walker reference), `src/walkers/README.md` (walker package conventions), `src/shared/` (`ServiceError`)
- **Planned components (created by the implementation WI, not yet on `main`):** `src/walkers/quant/` package (created by WI-4.2.2)
- **Exemplar:** none. No `docs/prd_exemplars/PRD-4.2-quant-walker.md` exists for v1; alignment with any future Quant Walker exemplar is an Open Question.

## Purpose

Provide the first walker implementation for the Quant Walker: a thin typed delegate that calls a single public function on the `risk_analytics` deterministic service and returns its typed output unchanged.

Walker v1 exists to establish the second walker package under `src/walkers/`, the entry point, the import hygiene, and the parity-test pattern for delegation against `risk_analytics`. It does not own quantitative interpretation, hierarchy localization, significance assessment, first-order vs second-order narrative, or any other walker-originated logic beyond what the deterministic service already produces.

All quantitative semantics — first-order delta construction, rolling statistics, volatility regime classification, volatility change-flag classification, status precedence (`UNSUPPORTED_MEASURE` → `MISSING_SNAPSHOT` → `MISSING_NODE` → in-object `DEGRADED` → `MISSING_COMPARE` → `MISSING_HISTORY` → `OK`), `data_version` / `service_version` propagation, and `generated_at` determinism — remain in `src/modules/risk_analytics/` as governed by PRD-1.1-v2. This PRD does not restate or alter PRD-1.1-v2 semantics.

## Why this is the v1 slice

The repository rule is: walkers interpret typed outputs from modules; they do not own canonical logic. PRD-4.1 (Data Controller Walker v1) established this delegation boundary against `controls_integrity`. The Quant Walker is the next walker in the standard investigation sequence (`docs/05_walker_charters.md`: Data Controller → Quant → Time Series → ...) and its upstream deterministic service (PRD-1.1-v2) is complete and stable on `main` with a public API surface (`get_risk_summary`, `get_risk_delta`, `get_risk_history`, `get_risk_change_profile`) and one canonical second-order typed contract (`RiskChangeProfile`).

Before the Quant Walker can add interpretive value (hierarchy localization, significance assessment, first- vs second-order narrative, candidate deeper-investigation generation), the delegation boundary against `risk_analytics` must exist and be tested. v1 establishes that boundary with the minimum viable implementation: call one public service function, return its result unchanged, prove parity. Richer walker behavior is a v2+ concern.

This is also the highest-leverage spec gap currently blocking the relay: without it, the next coding work item after PRD-5.1's WIs land has no PRD to anchor it, and `src/walkers/` stays single-occupant.

## In scope

- New `quant` package under `src/walkers/` (created by WI-4.2.2) with a single public entry point
- Entry point delegates exclusively to `get_risk_change_profile` from the public `risk_analytics` module API
- Walker returns the same typed union as the service: `RiskChangeProfile | ServiceError`
- No wrapper types, no semantic transformation, no additional fields
- Pass-through of all request inputs (`node_ref`, `measure_type`, `as_of_date`, `compare_to_date`, `lookback_window`, `require_complete`, `snapshot_id`, `fixture_index`) unchanged
- Unit tests proving output parity between walker and direct service calls across the documented success path and every documented `ServiceError` status code reachable from `get_risk_change_profile`

## Out of scope

- Any change to PRD-1.1-v2 service semantics, contracts, status precedence, or status vocabulary
- Hierarchy localization (e.g., identifying which node-level a move concentrates at)
- First-order vs second-order distinction as a walker-owned interpretive output (the underlying `RiskChangeProfile` already carries `delta_abs`, `delta_pct`, `volatility_regime`, `volatility_change_flag`; the walker does not synthesize narrative on top of these)
- Significance / materiality assessment of the change
- Candidate areas for deeper investigation (no walker-emitted prompts to other walkers)
- Quantitative-change summary narrative, recommended-next-step prose, free-text findings, walker-authored caveats
- Multi-target invocation, batch invocation, or hierarchy fan-out (single-target only in v1)
- Multi-measure synthesis (e.g., combined VaR + ES walker output) and any cross-measure aggregation
- Multi-function delegation in v1 — exposing additional delegates over `get_risk_summary`, `get_risk_delta`, or `get_risk_history` is deferred (see Walker contract → "One-vs-many delegate decision" and Open Questions)
- Concentration metrics, drill-down navigation, or other hierarchy-aware aggregations
- Walker-originated rolling-statistics, volatility classification, regime detection, or change-flag logic of any kind (these remain inside `get_risk_change_profile`)
- Recomputation, transformation, or interpretation of any field on `RiskChangeProfile` or `ServiceError`
- Telemetry adoption for the Quant Walker layer (defer to shared-infra adoption matrix; tracked separately as a future WI consistent with how the Data Controller Walker received telemetry post-v1)
- Orchestrator routing, daily-run integration, or any coupling to PRD-5.1 (PRD-5.1 v1 explicitly excludes quant walker integration; orchestrator routing is a PRD-5.1 v2+ concern)
- UI rendering, analyst review console, dashboard surfaces, governance sign-off
- Replay harness changes (walker adds no new snapshot, version, or evidence semantics; service outputs already carry replay context)
- Any new ADR-level concept, new typed status vocabulary, new error envelope, new evidence shape, or new shared-infra contract
- FRTB / PLA / HPL / RTPL stages, model risk usage walker concerns, or any non-`risk_analytics` upstream

## Users and consumers

Primary consumers of the walker entry point:

- Daily Risk Investigation orchestrator (future, PRD-5.1 v2+ — not built in v1; PRD-5.1 v1 explicitly excludes quant walker integration)
- Market Context Walker (future; per `docs/05_walker_charters.md`, Quant outputs are typical inputs to Market Context Walker)
- Governance / Reporting Walker (future)

All consumers receive the same `RiskChangeProfile | ServiceError` types that the service produces. The walker introduces no new types for consumers to handle.

## Walker contract

### Public entry point

The walker exposes a single function as its public entry point.

**Function name:** `summarize_change`

**Location:** `src/walkers/quant/` package (created by WI-4.2.2; module layout per existing walker conventions, exported via package `__init__.py` mirroring `src/walkers/data_controller/__init__.py`)

**Signature:**

```python
def summarize_change(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    compare_to_date: date | None = None,
    lookback_window: int = 60,
    require_complete: bool = False,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> RiskChangeProfile | ServiceError:
```

**Behavior:** Calls `get_risk_change_profile` with the same arguments and returns its result unchanged. The walker does not inspect, branch on, transform, or augment the returned `RiskChangeProfile` or `ServiceError`. Default values for optional parameters mirror PRD-1.1-v2 exactly (`lookback_window=60`, `require_complete=False`, all others `None`). Any future change to the underlying service's defaults must be reflected here in lockstep — the walker does not pin or override defaults.

### One-vs-many delegate decision (v1)

This PRD recommends **exactly one** entry point — `summarize_change` over `get_risk_change_profile` — for the v1 slice. Rationale:

1. The Quant Walker charter (`docs/05_walker_charters.md` lines 43–83) names "first-order movement, second-order instability, or both?" as a core question. `RiskChangeProfile` is the only `risk_analytics` typed contract that carries both first-order delta fields (`delta_abs`, `delta_pct`) and second-order volatility context (`volatility_regime`, `volatility_change_flag`) in one object. It is the closest single-function match to the walker's mission.
2. The smallest reviewable surface that establishes the delegation boundary is one delegate, mirroring PRD-4.1 which exposed exactly one entry point (`assess_integrity` over `get_integrity_assessment`).
3. There is no concrete downstream consumer in PRD-5.1 v1 (which excludes quant walker integration entirely). PRD-5.1 v2+ has not yet specified which `risk_analytics` functions a future quant routing slice will need; speculatively pre-exposing `get_risk_summary`, `get_risk_delta`, or `get_risk_history` delegates would push contract decisions ahead of any concrete requirement.
4. Adding further delegates later is purely additive (new entry-point functions in the same package), not a breaking change. Deferring is the safe direction.

This recommendation is registered explicitly as an Open Question (v2+) so that the issue planner and PM see it as a deferred decision rather than an oversight.

### Import rules

The walker must import the delegated function and its primary typed return type from the public `risk_analytics` module API:

- `from src.modules.risk_analytics import RiskChangeProfile, get_risk_change_profile`

The walker must not import:

- `src.modules.risk_analytics.service` directly
- Any private helper, internal constant, or non-`__all__` symbol from `src.modules.risk_analytics` or its submodules
- Any classifier internal to volatility logic (e.g., `_classify_volatility_regime`, `_classify_volatility_change_flag`) — these are private service helpers
- Any other deterministic-service module not strictly required to type the entry-point signature
- Anything from `agent_runtime`

Type imports needed for the signature must use the same public submodule paths that the sibling Data Controller Walker uses, consistent with `src/walkers/data_controller/walker.py` precedent on `main`:

- `from src.modules.risk_analytics.contracts import MeasureType, NodeRef`
- `from src.modules.risk_analytics.fixtures import FixtureIndex`
- `from src.shared import ServiceError`
- `from datetime import date`

### Output type

`RiskChangeProfile | ServiceError`

This is the same typed union returned by `get_risk_change_profile`. The walker does not wrap, extend, or transform this union.

### No wrapper types

The walker must not introduce:

- A `WalkerResult`, `WalkerOutcome`, `QuantResult`, `QuantWalkerOutput`, `QuantAssessment`, `ChangeAssessment`, or any similar wrapper type
- Additional fields on the return path (no `walker_metadata`, `walker_trace`, no walker-authored `caveats`, no walker-authored `recommended_next_step`, no walker-authored `significance`, no walker-authored `hierarchy_localization`)
- A parallel error type or error-code vocabulary
- Any new in-object status vocabulary or enum

## Error handling

The walker propagates all error semantics from `get_risk_change_profile` unchanged.

Returned typed `ServiceError` cases (each carries `operation="get_risk_change_profile"`, a `status_code`, and `status_reasons`):

- `UNSUPPORTED_MEASURE` — requested `measure_type` is outside the operation's governed contract for the pinned fixture pack
- `MISSING_SNAPSHOT` — pinned `snapshot_id` not found, or no snapshot exists for `as_of_date`
- `MISSING_NODE` — current snapshot exists but the scoped node and measure cannot be resolved in it

Raised `ValueError` cases (request validation; the walker does not catch or re-wrap):

- `lookback_window` is not `60` (per PRD-1.1-v2 v1 constraint)
- `snapshot_id` is provided but blank
- `compare_to_date` is later than `as_of_date`

The walker adds no new error codes, no new error types, no new `status_reasons`, and no fallback behavior. In-object statuses (`OK`, `DEGRADED`, `MISSING_COMPARE`, `MISSING_HISTORY`) on a returned `RiskChangeProfile` are pass-through and unchanged.

## Replay and evidence

The walker adds no replay or evidence semantics of its own. All replay and evidence guarantees are satisfied by the service output, which already carries:

- `snapshot_id` — pinned snapshot context (ADR-002)
- `data_version` — data version for replay (ADR-002)
- `service_version` — service version for replay (ADR-002)
- `generated_at` — deterministic timestamp (ADR-002)
- `status` and `status_reasons` — typed structured diagnostics for both success and `ServiceError` paths (ADR-001, ADR-003)

For typed `ServiceError` returns, replay-relevant context is carried on `ServiceError.operation`, `ServiceError.status_code`, and `ServiceError.status_reasons`; the walker propagates these unchanged.

The walker does not strip, modify, or supplement any of these fields. The walker does not introduce a separate evidence shape, separate trace shape, or separate version field.

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
- Walker package location is `src/walkers/quant/` per `src/walkers/README.md`
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

If existing fixtures do not cover one or more of these rows directly, the coding agent must cover the maximal subset reachable with current fixtures and record the unreached rows as fixture gaps in the implementation PR. Do not introduce new fixture infrastructure for v1; gaps roll into the v2+ Open Questions.

Optional secondary parity rows (cover when fixtures already exist; do not block v1 if they do not):

- in-object `DEGRADED` (current point, compare point, or history degradation) on a returned `RiskChangeProfile`
- in-object `MISSING_COMPARE` when no prior business day or compare snapshot exists
- in-object `MISSING_HISTORY` when no valid history points exist in the lookback window
- distinct `volatility_regime` values (e.g., `INSUFFICIENT_HISTORY`, `LOW`, `NORMAL`, `ELEVATED`, `HIGH`) and `volatility_change_flag` values (e.g., `INSUFFICIENT_HISTORY`, `STABLE`, `RISING`, `FALLING`) — only as parity rows; the walker does not classify, it only propagates

## Issue decomposition guidance

This PRD is implemented by at most two work items:

- **WI-4.2.1** — Quant Walker v1 implementation PRD (this document; mirrors WI-4.1.1)
- **WI-4.2.2** — Quant Walker delegate slice: thin facade in a new `src/walkers/quant/` package + parity tests (mirrors WI-4.1.2)

Sequencing:

1. WI-4.2.1 (this PRD) merges first
2. WI-4.2.2 is promoted from `blocked/` to `ready/`
3. Coding agent implements WI-4.2.2 against this PRD
4. Review agent reviews against this PRD and the WI-4.2.2 acceptance criteria

No further decomposition is needed for v1. Telemetry adoption, multi-delegate expansion, narrative behavior, and orchestrator routing are out of scope for this PRD and must be tracked as separate WIs against future PRDs (PRD-4.2-v2 / PRD-5.1-v2 / a follow-on telemetry adoption WI per `docs/shared_infra/adoption_matrix.md`).

## Open questions (v2+ only — none block v1)

- **Richer walker narrative:** v2+ may add walker-authored interpretive outputs (quantitative-change summary text, hierarchy localization, significance assessment, candidate-areas-for-deeper-investigation, recommended-next-step). These would require new output fields, a new wrapper type, and an exemplar / methodology review. Deferred until the delegation boundary is proven and a concrete downstream consumer (orchestrator or another walker) is specified.
- **Hierarchy localization:** Identifying which `node_level` or sub-scope a change concentrates at requires either multi-node walker invocation or an upstream service capability that does not exist on `main` today. Out of scope for v1.
- **First-order vs second-order distinction as walker output:** `RiskChangeProfile` already carries first-order (`delta_abs`, `delta_pct`) and second-order (`volatility_regime`, `volatility_change_flag`) fields side-by-side. Whether the walker should synthesize a combined "first-order movement vs second-order instability" interpretation, and what type that should be, is deferred to v2+.
- **Multi-measure or batch invocation:** v1 is single-target, single-measure only. Batch and multi-measure synthesis (e.g., combined VaR + ES walker output) are deferred. Multi-target fan-out is an orchestrator concern, not a walker v1 concern.
- **Multi-function delegation:** v1 exposes only `summarize_change` over `get_risk_change_profile`. Whether to add walker-level delegates for `get_risk_summary`, `get_risk_delta`, or `get_risk_history` should be driven by a concrete downstream consumer requirement (e.g., a PRD-5.1 v2+ quant routing slice that needs a fast first-order delta path). Pre-exposing them in v1 would push contract decisions ahead of any concrete requirement.
- **Telemetry adoption:** The shared-infra adoption matrix lists `src/walkers/` telemetry as adopted only for the Data Controller Walker (WI-4.1.4). A separate WI should add telemetry to the Quant Walker once that pattern is being applied across walkers; v1 does not require it. When that WI lands, the adoption matrix row for `src/walkers/` should be updated to reflect Quant Walker coverage.
- **Quant Walker exemplar alignment:** No exemplar exists at `docs/prd_exemplars/PRD-4.2-quant-walker.md`. If one is authored, this PRD should be reviewed for alignment before any v2+ behavior is added. The exemplar must be treated as non-normative for v1 unless and until a future PRD update adopts it.

## Reviewer checklist

- Walker v1 is delegation-only; no quant logic, no rolling-statistics, no volatility classification, and no narrative generation in the walker
- Output type is `RiskChangeProfile | ServiceError` — no wrapper types, no additional fields, no new status vocabulary
- PRD-1.1-v2 semantics (status precedence, delta-field rules, volatility-rules-v1, replay/version metadata) are cross-referenced, not restated or altered
- Exemplar-only / interpretive fields (any quantitative-change narrative, hierarchy localization, significance assessment, first-/second-order distinction, recommended-next-step prose, candidate deeper-investigation prompts) are explicitly out of scope for v1
- Import rules restrict the walker to the public `risk_analytics` module API plus the established type submodule imports used by `src/walkers/data_controller/walker.py`; no private helpers, no classifier internals, no `agent_runtime` imports, no `src.modules.risk_analytics.service` direct import
- Walker signature defaults exactly mirror `get_risk_change_profile` defaults; no walker-pinned overrides
- Replay and evidence expectations defer to service outputs per ADR-002 and ADR-003; the walker introduces no `data_version`, `service_version`, `snapshot_id`, `generated_at`, or evidence-shape concept of its own
- Error handling is pass-through: `ServiceError` and `ValueError` propagate unchanged with no walker-introduced fallback or re-wrap
- One-vs-many delegate decision is honored (exactly one entry point in v1); any additional delegate requires a v2+ PRD update tied to a concrete downstream consumer
- No coupling to PRD-5.1 v1 orchestrator code; the orchestrator is named only as a future consumer
- Acceptance criteria and parity matrix are sufficient for WI-4.2.2 coding without guesswork
- No new ADR-level concept, no new shared-infra contract, no schema change to PRD-1.1-v2 contracts has leaked in
- Telemetry remains out of scope for v1; if telemetry is added in the implementation PR, the reviewer should require either (a) a separate, explicit walker-telemetry WI linked from the PR, or (b) removal of the telemetry from v1 — consistent with PRD-4.1's original v1 scope discipline
- Backtick-wrapped repository paths in this PRD either exist on `main` (`src/modules/risk_analytics/`, `src/modules/risk_analytics/contracts/`, `src/modules/risk_analytics/fixtures/`, `src/walkers/data_controller/`, `src/walkers/README.md`, `src/shared/`, all `docs/...` paths) or are explicitly called out as planned with a linked work item in the header (`src/walkers/quant/` — created by WI-4.2.2), consistent with reference-integrity and registry-alignment checks

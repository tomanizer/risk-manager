# PRD-4.3: Time Series Walker v1

## Header

- **PRD ID:** PRD-4.3
- **Title:** Time Series Walker v1 — Interpretive Walker Over `RiskChangeProfile`
- **Phase:** Phase 2
- **Status:** Ready for implementation
- **Layer:** Walker
- **Type:** Single-call interpretive delegate with typed wrapper output
- **Primary owner:** Technical Owner, Time Series Walker
- **Upstream service PRD:** PRD-1.1-v2 (Risk Summary Service v2)
- **Sibling walker PRDs (pattern only, not contracts):** PRD-4.1 (Data Controller Walker v1), PRD-4.2 (Quant Walker v1)
- **Future consumer (not built in v1):** PRD-5.1-v2 (Daily Risk Investigation Orchestrator multi-walker routing); Governance / Reporting Walker v1 (post-MVP near-term, to be authored once this PRD is in draft per `docs/roadmap/module_1_var_dashboard.md` DECISION-MVP-02)
- **Related ADRs:** ADR-001 (schema and typing), ADR-002 (replay and snapshot model), ADR-003 (evidence and trace model), ADR-004 (business-day and calendar handling)
- **Related shared infra:** `docs/shared_infra/index.md`, `docs/shared_infra/telemetry.md`, `docs/shared_infra/adoption_matrix.md`
- **Related canon:** `docs/05_walker_charters.md` (Time Series Walker charter), `docs/roadmap/module_1_var_dashboard.md` (Module 1 MVP scope and closed decisions DECISION-MVP-01 / DECISION-MVP-02)
- **Related components (existing on `main`):** `src/modules/risk_analytics/` (service), `src/modules/risk_analytics/contracts/` (typed contracts: `RiskChangeProfile`, `VolatilityRegime`, `VolatilityChangeFlag`, `SummaryStatus`, `MeasureType`, `NodeRef`), `src/modules/risk_analytics/fixtures/` (`FixtureIndex`, `build_fixture_index`), `src/walkers/data_controller/` and `src/walkers/quant/` (sibling walkers; structural reference only), `src/walkers/README.md` (walker package conventions), `src/shared/` (`ServiceError`), `src/shared/telemetry/` (`emit_operation`, `node_ref_log_dict`, `timer_start`)
- **Planned components (created by the implementation WIs, not yet on `main`):** `src/walkers/time_series/` package (created by WI-4.3.2) <!-- drift-ignore -->
- **Exemplar:** none. No `docs/prd_exemplars/PRD-4.3-time-series-walker.md` exists for v1; alignment with any future Time Series Walker exemplar is registered as a v2+ Open Question.

## Purpose

Provide the first walker implementation for the Time Series Walker: a typed interpretive delegate that calls a single public function on the `risk_analytics` deterministic service (`get_risk_change_profile`) and returns either a typed walker-authored `TimeSeriesAssessment` or the upstream `ServiceError` unchanged.

Walker v1 establishes the third walker package under `src/walkers/`, the entry point, the import hygiene, the typed-wrapper output pattern for interpretive walkers, and the parity-and-classification test pattern. It owns all interpretive vocabularies and inference rules required for time-series interpretation in Module 1 MVP — these are fully enumerated in this PRD with deterministic mappings over upstream typed fields.

All deterministic time-series computation — rolling statistics, volatility regime classification, volatility change-flag classification, status precedence, replay/version metadata — remains in `src/modules/risk_analytics/` as governed by PRD-1.1-v2. This PRD does not restate or alter PRD-1.1-v2 semantics.

## Why this is the v1 slice (delegation-only vs interpretive)

### Decision

**v1 includes interpretive output.** The walker delegates to `get_risk_change_profile`, then constructs a typed `TimeSeriesAssessment` wrapper carrying walker-authored interpretive fields (trend assessment, outlier flag, regime-change signal, volatility direction, current z-score, confidence, caveat codes) plus the upstream `RiskChangeProfile` propagated by reference as evidence.

### Rationale

1. **Module 1 MVP requires it.** `docs/roadmap/module_1_var_dashboard.md` and `docs/registry/current_state_registry.yaml` (entry `WALKER-TIME-SERIES`) record the Time Series Walker MVP gap as "full time-series interpretation capability" with `next_needed_prd: PRD-TBD-Time-Series-Walker-v1`. There is no Time Series Walker v2 PRD in the roadmap. Authoring a delegation-only v1 followed by an interpretive v2 would create two PRDs, two implementation cycles, and two coding/review passes for a capability that can be specified in one bounded slice today.
2. **Sibling delegation-only v1 was justified by an absent or partial upstream interpretive contract.** PRD-4.1 (Data Controller Walker) delegated to `get_integrity_assessment` because that service already produces a fully interpreted `IntegrityAssessment` (trust state, false-signal risk, blocking/cautionary reason codes). PRD-4.2 (Quant Walker) delegated to `get_risk_change_profile` because the upstream object already carries first-order delta and second-order volatility fields suitable for downstream consumption without further interpretation. The Time Series Walker, in contrast, must produce a **trend/outlier/regime classification** that is not present on any `risk_analytics` typed output — so a delegation-only v1 would not satisfy MVP.
3. **All required inference is deterministic over typed upstream fields.** `RiskChangeProfile` already carries `current_value`, `rolling_mean`, `rolling_std`, `rolling_min`, `rolling_max`, `history_points_used`, `volatility_regime`, `volatility_change_flag`, `status`, `status_reasons`, and full replay metadata. Every classification rule in this PRD is a deterministic mapping over these fields. The walker does not introduce stochastic models, scenario logic, narrative LLM logic, or any computation that would belong inside `risk_analytics`.
4. **DECISION-MVP-02 (Governance / Reporting Walker post-MVP) depends on this output shape.** Per `docs/roadmap/module_1_var_dashboard.md`, the Governance / Reporting Walker v1 PRD will be authored "immediately after Quant Walker v2 and Time Series Walker v1 PRDs are in draft, not after their implementations are complete." Specifying `TimeSeriesAssessment` in this PRD unblocks that downstream PRD authoring without further negotiation.

### Why this is the narrowest reviewable interpretive slice

- one upstream call (`get_risk_change_profile`) — not two (`get_risk_history` is explicitly out of scope for v1; see `Upstream dependency` below)
- one new typed wrapper type and five small enums
- one entry point with the same parameter hygiene as `summarize_change` (PRD-4.2)
- five interpretive classification axes (trend, outlier, regime change, volatility direction, confidence) — each with a deterministic precedence-ordered rule table fully enumerated in this PRD
- one telemetry event (`assess_time_series`) emitted via the shared telemetry contract

Richer behavior (multi-target, multi-measure, raw-history-series exposure, narrative caveats, recommended-next-step prose, hierarchy fan-out, Data Controller trust-gate consumption) is a v2+ concern and is explicitly out of scope.

## In scope

- New `time_series` package under `src/walkers/`, created by WI-4.3.2 <!-- drift-ignore -->
- Single public entry point `assess_time_series` over the public `get_risk_change_profile` API
- New typed wrapper output `TimeSeriesAssessment` plus five supporting `StrEnum` vocabularies (`TrendAssessment`, `OutlierFlag`, `RegimeChangeSignal`, `TimeSeriesConfidence`, `TimeSeriesCaveatCode`) — defined under `src/walkers/time_series/contracts/` (or equivalent module layout per existing walker conventions)
- Deterministic walker-owned classification rules over `RiskChangeProfile` typed fields (current value, rolling mean/std/min/max, history points used, volatility regime, volatility change flag, status), fully enumerated in this PRD
- Confidence-level inference deterministically derived from upstream typed fields (`history_points_used`, `status`, `volatility_regime`)
- Caveat-code emission deterministically derived from upstream typed fields and from the walker's own classification outcomes
- Pass-through of all `ServiceError` cases from `get_risk_change_profile` (`UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`) and pass-through of all `ValueError` request-validation cases
- Walker output carries the upstream `RiskChangeProfile` by reference as nested typed evidence (no recomputation, no field substitution)
- Walker version pinned at module level (`WALKER_VERSION = "time_series-v1.0.0"`)
- `generated_at` deterministically equal to the upstream `RiskChangeProfile.generated_at` (no wall-clock dependency)
- Telemetry: one structured `emit_operation` event per call with status mapped from upstream outcome, payload aligned with `docs/shared_infra/telemetry.md`, status-to-level mapping owned by shared telemetry helpers
- Adoption matrix update: extend the `src/walkers/` row Notes to record Time Series Walker telemetry coverage when WI-4.3.4 lands
- Unit tests covering (a) classification truth tables for every enum value and every documented rule branch, (b) confidence rule precedence, (c) caveat-code emission, (d) `ServiceError` and `ValueError` propagation parity with the underlying service, (e) replay determinism (equal upstream → equal walker output), (f) telemetry payload discipline

## Out of scope

- Any change to PRD-1.1-v2 service semantics, contracts, status precedence, status vocabulary, rolling-statistics rules, volatility-rules-v1 (`VOLATILITY_RULES_V1`), or replay/version metadata
- Calls to `get_risk_history`, `get_risk_summary`, or `get_risk_delta` from this walker in v1 (see `Upstream dependency` for the explicit rationale; integration of `get_risk_history` is a v2+ Open Question)
- Consumption of Data Controller Walker output (`IntegrityAssessment`) as a trust-gate input inside this walker; trust-state-driven routing is an orchestrator (PRD-5.1-v2) concern (see `Upstream dependency` and `Open questions`)
- Multi-target, multi-measure, batch invocation, or hierarchy fan-out (single-target, single-measure only in v1)
- Walker-owned business-day reasoning, calendar-day windowing, or any independent resolution of business days (forbidden by ADR-004 — defer entirely to upstream)
- Walker-owned rolling-statistics, regime calculation, or change-flag calculation of any kind (these remain inside `get_risk_change_profile`)
- Recomputation, transformation, or reinterpretation of any field on `RiskChangeProfile` or `ServiceError`
- Free-text narrative, recommended-next-step prose, walker-authored human-readable findings, hierarchical localization narrative
- Exposing the raw `RiskHistorySeries` (ordered points) on the walker output (consumers needing raw points call `get_risk_history` directly)
- Multi-function delegation (only `get_risk_change_profile` is invoked in v1)
- Stochastic forecasting, scenario simulation, Monte Carlo over the series, or any non-deterministic interpretation
- Cross-walker synthesis (no consumption of other walker outputs; no emission to other walkers)
- Materiality, significance, or escalation thresholds (orchestrator concern in PRD-5.1-v2; absent in v1)
- Orchestrator routing, daily-run integration, or any coupling to PRD-5.1; PRD-5.1 v1 explicitly excludes time-series walker integration; PRD-5.1-v2 will add it
- UI rendering, analyst review console, dashboard surfaces, governance sign-off
- Replay-harness changes beyond what the walker output naturally supports (the walker introduces no new snapshot, version, or evidence semantics beyond its own pinned `walker_version`)
- Any new ADR-level concept, new typed status vocabulary on the upstream service, new shared error envelope, new shared evidence-reference contract, or new shared-infra contract
- FRTB / PLA / HPL / RTPL stages, model-risk-walker concerns, market-context concerns, or any non-`risk_analytics` upstream
- Live-data integration (post-MVP per DECISION-MVP-01)
- Production database persistence, durable run state (post-MVP per DECISION-MVP-01)

## Users and consumers

Primary consumers of the walker entry point:

- Daily Risk Investigation Orchestrator multi-walker routing (PRD-5.1-v2; not built in v1)
- Governance / Reporting Walker v1 (post-MVP near-term per DECISION-MVP-02; will consume `TimeSeriesAssessment` for narrative synthesis)

Secondary consumers (not built in v1):

- Critic / Challenge Walker (future; will read `TimeSeriesAssessment.confidence` and `caveat_codes` to identify weak interpretive support)
- Presentation / Visualization Walker (future; may render `trend_assessment`, `outlier_flag`, `regime_change_signal`, and `current_z_score` as visual glyphs)

The walker introduces exactly one new typed object (`TimeSeriesAssessment`) and five new `StrEnum` vocabularies that downstream consumers must handle.

## Walker contract

### Public entry point

The walker exposes a single function as its public entry point.

**Function name:** `assess_time_series`

**Location:** `src/walkers/time_series/` package (created by WI-4.3.2; module layout per existing walker conventions, exported via package `__init__.py` mirroring `src/walkers/data_controller/__init__.py` and `src/walkers/quant/__init__.py`) <!-- drift-ignore -->

**Signature:**

```python
def assess_time_series(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    compare_to_date: date | None = None,
    lookback_window: int = 60,
    require_complete: bool = False,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> TimeSeriesAssessment | ServiceError:
```

Default values mirror `get_risk_change_profile` exactly (`lookback_window=60`, `require_complete=False`, all other optionals default `None`). Any future change to the underlying service's defaults must be reflected here in lockstep — the walker does not pin or override defaults.

### Behavior

1. Call `get_risk_change_profile(node_ref, measure_type, as_of_date, compare_to_date, lookback_window, require_complete, snapshot_id, fixture_index)`.
2. If the call returns a `ServiceError`, return it unchanged. No partial `TimeSeriesAssessment` is constructed in any error path.
3. If the call returns a `RiskChangeProfile`, construct a `TimeSeriesAssessment` per the `Classification vocabularies and inference rules` section below and return it.
4. `ValueError` raised by request validation propagates from the walker unchanged (the walker does not catch or re-wrap).

The walker must not re-call the service, retry, or perform any fallback resolution. Each invocation makes exactly one call to `get_risk_change_profile`.

### Upstream dependency

#### `risk_analytics` functions invoked

- `get_risk_change_profile` — exactly one call per invocation; returns `RiskChangeProfile | ServiceError`.

#### Functions explicitly NOT invoked in v1

- `get_risk_history` — see rationale below.
- `get_risk_summary` — superseded by `get_risk_change_profile` for this walker (which returns a superset of `RiskSummary` fields plus volatility context).
- `get_risk_delta` — superseded by `get_risk_change_profile` for this walker.

#### Why `get_risk_change_profile` only (and not also `get_risk_history`)

The user task framing notes that `get_risk_history` is "the natural upstream for time-series interpretation" because the walker charter lists "risk history series" as the first typical input. This PRD makes the deliberate decision to defer `get_risk_history` integration to v2+ for the following reasons:

1. **Sufficiency of the existing typed surface.** Every walker-charter core question (`is this move unusual relative to history?`, `is volatility rising or falling?`, `is the series noisy, stable, or regime-changing?`, `does the current point look like an outlier?`) is answerable from the `RiskChangeProfile` typed fields:
   - `current_value`, `rolling_mean`, `rolling_std` → outlier z-score, trend-relative-to-baseline classification
   - `volatility_regime` → noisy / stable / regime characterization
   - `volatility_change_flag` → volatility direction (rising / falling / stable)
   - `history_points_used`, `status` → confidence and caveat inputs

   `RiskChangeProfile` already encapsulates the deterministic baseline-window rolling statistics (sample standard deviation over 60 business days ending on `as_of_date`, inclusive — see PRD-1.1-v2 `Window policy` and `Volatility policy`) and the deterministic short-window vs baseline-window dispersion ratio used to classify the change flag. There is nothing the walker can compute from the raw points that the service has not already computed deterministically.

2. **ADR-004 boundary discipline.** ADR-004 forbids walker-owned business-day reasoning. `get_risk_history` takes calendar `start_date` and `end_date` and returns whatever points fall in that inclusive range; matching its returned set to the same 60-business-day baseline window used by `get_risk_change_profile` would require the walker to either independently resolve business days (forbidden) or pass a calendar-day overshoot (which produces a non-aligned point set and creates an impedance mismatch with `RiskChangeProfile.history_points_used`).

3. **Replay-safety and parity-test simplicity.** A single upstream call gives a single `snapshot_id`/`data_version`/`service_version` triple to propagate as evidence. A two-call composition would force the walker to assert cross-call replay invariants (matching snapshot context, matching data version) that PRD-1.1-v2 does not currently make explicit at the cross-operation level.

4. **No concrete v1 consumer requires the raw series via this walker's surface.** PRD-5.1-v2 routing has not been authored yet; the Governance / Reporting Walker v1 is post-MVP; the Presentation / Visualization Walker is post-MVP. If a future consumer needs the raw series alongside the interpretation, it can either call `get_risk_history` directly itself or trigger a v2+ revision of this walker that exposes a `TimeSeriesAssessment.history_series: RiskHistorySeries | None` field and adds the second upstream call. Adding it later is purely additive.

5. **Adding it later is non-breaking.** Extending `TimeSeriesAssessment` with a new optional `history_series` field and adding a second upstream call is an additive change. Removing it later would be a breaking change. Deferring is the safe direction.

This decision is registered explicitly in `Open questions` so that the issue planner and PM see it as a deferred decision rather than an oversight.

#### Data Controller Walker as a trust-gate input — explicit decision

**Decision:** The Time Series Walker v1 is **independent**. It does not consume `IntegrityAssessment` from the Data Controller Walker as an input or gate. It reads `risk_analytics` directly via `get_risk_change_profile`.

**Rationale:**

- Walker boundary discipline: walkers are independent specialist consumers; they do not chain other walkers. Cross-walker routing is an orchestrator concern.
- PRD-5.1-v2 (multi-walker orchestration) is the explicit owner of trust-state-driven routing logic. The orchestrator will decide, based on Data Controller trust state, whether to invoke the Time Series Walker for a given target. Embedding that decision inside the walker would duplicate trust-gate logic across multiple walkers and would couple the walker's tests to controls-integrity fixtures.
- The walker carries its own `confidence` field that reflects upstream-data sufficiency from `RiskChangeProfile` typed fields (`history_points_used`, `status`, `volatility_regime`). This is independent of, and complementary to, Data Controller trust state.
- This contract gives PRD-5.1-v2 a clean orchestrator-level decision surface: route to `assess_time_series` only when Data Controller trust state permits; otherwise skip.

This decision is reflected in the orchestrator routing contract in `Downstream consumer contract`.

### Import rules

The walker must import from public surfaces only:

```python
from src.modules.risk_analytics import RiskChangeProfile, get_risk_change_profile
from src.modules.risk_analytics.contracts import (
    MeasureType,
    NodeRef,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.shared import ServiceError
from src.shared.telemetry import emit_operation, node_ref_log_dict, timer_start
from datetime import date, datetime
```

The walker must not import:

- `src.modules.risk_analytics.service` directly
- Any private helper, classifier internal, or non-`__all__` symbol from `src.modules.risk_analytics` or its submodules (e.g., `_classify_volatility_regime`, `_classify_volatility_change_flag`, `_BASELINE_WINDOW`, `_SHORT_WINDOW`)
- `src.modules.controls_integrity.*` (the walker is independent of Data Controller in v1; see `Upstream dependency` above)
- Any other walker package (`src.walkers.data_controller`, `src.walkers.quant`)
- Anything from `agent_runtime`

### Output type: `TimeSeriesAssessment`

A new frozen typed model (per ADR-001) under the walker package contracts module.

**Fields (all required unless noted; frozen, `extra="forbid"`):**

| Field | Type | Source / derivation |
| --- | --- | --- |
| `node_ref` | `NodeRef` | mirrored from `risk_change_profile.node_ref` |
| `measure_type` | `MeasureType` | mirrored from `risk_change_profile.measure_type` |
| `as_of_date` | `date` | mirrored from `risk_change_profile.as_of_date` |
| `compare_to_date` | `date \| None` | mirrored from `risk_change_profile.compare_to_date` |
| `trend_assessment` | `TrendAssessment` | classification rule below |
| `outlier_flag` | `OutlierFlag` | classification rule below |
| `volatility_regime` | `VolatilityRegime` | propagated unchanged from `risk_change_profile.volatility_regime` |
| `volatility_direction` | `VolatilityChangeFlag` | propagated unchanged from `risk_change_profile.volatility_change_flag` |
| `regime_change_signal` | `RegimeChangeSignal` | classification rule below |
| `current_z_score` | `float \| None` | derivation rule below; `None` when not computable |
| `confidence` | `TimeSeriesConfidence` | confidence rule below |
| `caveat_codes` | `tuple[TimeSeriesCaveatCode, ...]` | caveat rule below; deduplicated, lexicographically ascending; defaults to empty tuple |
| `risk_change_profile` | `RiskChangeProfile` | the upstream typed object, propagated by reference (frozen nested model) |
| `snapshot_id` | `str` | mirrored from `risk_change_profile.snapshot_id` |
| `walker_version` | `str` | module-level constant (`WALKER_VERSION = "time_series-v1.0.0"`); non-empty |
| `generated_at` | `datetime` | equal to `risk_change_profile.generated_at` (no wall-clock dependency) |

**Mirrored-field invariants** (enforced by a `model_validator(mode="after")`):

- `node_ref == risk_change_profile.node_ref`
- `measure_type == risk_change_profile.measure_type`
- `as_of_date == risk_change_profile.as_of_date`
- `compare_to_date == risk_change_profile.compare_to_date`
- `volatility_regime == risk_change_profile.volatility_regime`
- `volatility_direction == risk_change_profile.volatility_change_flag`
- `snapshot_id == risk_change_profile.snapshot_id`
- `generated_at == risk_change_profile.generated_at`
- `walker_version` non-empty

Any mismatch raises `ValueError`.

**No additional fields beyond those listed.** No walker-authored `narrative`, `recommended_next_step`, `findings`, `evidence_refs`, or `walker_metadata` are introduced. Replay/version metadata for the upstream service (`data_version`, `service_version`, `status`, `status_reasons`) is reachable via the nested `risk_change_profile` and is not duplicated at the wrapper level (consistent with PRD-5.1's `TargetInvestigationResult` pattern that nests `IntegrityAssessment` by reference rather than re-shaping it).

### Supporting enums (StrEnum, frozen vocabularies; closed in v1)

```python
class TrendAssessment(StrEnum):
    NEAR_BASELINE = "NEAR_BASELINE"
    ELEVATED_VS_BASELINE = "ELEVATED_VS_BASELINE"
    SUPPRESSED_VS_BASELINE = "SUPPRESSED_VS_BASELINE"
    EXTREME_ELEVATED_VS_BASELINE = "EXTREME_ELEVATED_VS_BASELINE"
    EXTREME_SUPPRESSED_VS_BASELINE = "EXTREME_SUPPRESSED_VS_BASELINE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"

class OutlierFlag(StrEnum):
    NOT_OUTLIER = "NOT_OUTLIER"
    OUTLIER = "OUTLIER"
    EXTREME_OUTLIER = "EXTREME_OUTLIER"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"

class RegimeChangeSignal(StrEnum):
    STABLE_REGIME = "STABLE_REGIME"
    VOLATILITY_TRENDING = "VOLATILITY_TRENDING"
    REGIME_SHIFTING = "REGIME_SHIFTING"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"

class TimeSeriesConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"

class TimeSeriesCaveatCode(StrEnum):
    DEGRADED_UPSTREAM = "DEGRADED_UPSTREAM"
    INSUFFICIENT_HISTORY_FOR_OUTLIER = "INSUFFICIENT_HISTORY_FOR_OUTLIER"
    INSUFFICIENT_HISTORY_FOR_TREND = "INSUFFICIENT_HISTORY_FOR_TREND"
    INSUFFICIENT_HISTORY_FOR_VOLATILITY = "INSUFFICIENT_HISTORY_FOR_VOLATILITY"
    MISSING_COMPARE_POINT = "MISSING_COMPARE_POINT"
    MISSING_HISTORY_WINDOW = "MISSING_HISTORY_WINDOW"
    ZERO_VARIANCE_BASELINE = "ZERO_VARIANCE_BASELINE"
```

These vocabularies are closed in v1. Any addition requires a PRD update and a `walker_version` bump.

### No additional wrapper types

The walker must not introduce:

- A `WalkerResult`, `WalkerOutcome`, `TimeSeriesResult`, `TimeSeriesOutcome`, or any wrapper type beyond `TimeSeriesAssessment`
- A parallel error type or error-code vocabulary (the walker propagates the shared `ServiceError` unchanged)
- Any new in-object status vocabulary (the walker's outcome categories are: a typed `TimeSeriesAssessment`, or the upstream `ServiceError`; no third path)
- A walker-owned evidence-reference type or trace-context envelope (deferred until a shared-contract slice defines the canonical repo-wide objects per ADR-003 and PRD-1.1-v2 `Replay requirements`)

## Classification vocabularies and inference rules

All rules below are deterministic mappings over typed fields already present on `RiskChangeProfile`. They make no assumption about fields not enumerated here. They are version-pinned to `walker_version = "time_series-v1.0.0"`. Any change to thresholds, precedence, or vocabulary requires a `walker_version` bump and replay-fixture refresh, mirroring PRD-1.1-v2 `VOLATILITY_RULES_V1` discipline.

### Z-score derivation

`current_z_score` is a `float | None` derived from `risk_change_profile`:

- `current_z_score = (risk_change_profile.current_value - risk_change_profile.rolling_mean) / risk_change_profile.rolling_std`, **only if** all of the following hold:
  - `risk_change_profile.rolling_mean is not None`
  - `risk_change_profile.rolling_std is not None`
  - `risk_change_profile.rolling_std > 0` (strict; zero-variance baselines yield `None`)
- otherwise `current_z_score = None`

The threshold `> 0` (rather than `!= 0`) excludes negative-std edge cases that are mathematically impossible from `risk_analytics` (sample std is non-negative) but defends against future contract drift.

### Trend assessment

`trend_assessment` is determined by the following precedence (top-to-bottom; first match wins):

1. `INSUFFICIENT_HISTORY` if `current_z_score is None`
2. `EXTREME_ELEVATED_VS_BASELINE` if `current_z_score >= 3.0`
3. `EXTREME_SUPPRESSED_VS_BASELINE` if `current_z_score <= -3.0`
4. `ELEVATED_VS_BASELINE` if `current_z_score >= 1.0`
5. `SUPPRESSED_VS_BASELINE` if `current_z_score <= -1.0`
6. `NEAR_BASELINE` otherwise (`-1.0 < current_z_score < 1.0`)

The thresholds `1.0` and `3.0` are dimensionless z-score bands chosen to align with informal "one-sigma" and "three-sigma" moves, treated as a closed v1 deterministic convention. They are not regulatory; any change is a v2+ matter requiring a PRD update and `walker_version` bump.

### Outlier flag

`outlier_flag` is determined by the following precedence (top-to-bottom; first match wins):

1. `INSUFFICIENT_HISTORY` if `current_z_score is None`
2. `EXTREME_OUTLIER` if `abs(current_z_score) >= 3.0`
3. `OUTLIER` if `abs(current_z_score) >= 2.0`
4. `NOT_OUTLIER` otherwise (`abs(current_z_score) < 2.0`)

The thresholds `2.0` and `3.0` are dimensionless z-score bands chosen to align with informal "two-sigma" and "three-sigma" outlier conventions; same change-discipline notes as above.

Trend assessment and outlier flag are derived from the same `current_z_score` but answer different questions — trend is direction-aware (signed); outlier flag is magnitude-only (absolute). Both can independently report `INSUFFICIENT_HISTORY` from the same root cause.

### Volatility regime

Propagated unchanged from `risk_change_profile.volatility_regime`. The walker does not reclassify, override, or override `INSUFFICIENT_HISTORY`. Permitted values: `LOW`, `NORMAL`, `ELEVATED`, `HIGH`, `INSUFFICIENT_HISTORY` (per PRD-1.1-v2).

### Volatility direction

Propagated unchanged from `risk_change_profile.volatility_change_flag`. Permitted values: `STABLE`, `RISING`, `FALLING`, `INSUFFICIENT_HISTORY` (per PRD-1.1-v2).

### Regime-change signal

`regime_change_signal` is determined by the following precedence (top-to-bottom; first match wins):

1. `INSUFFICIENT_HISTORY` if `volatility_regime == VolatilityRegime.INSUFFICIENT_HISTORY` **or** `volatility_direction == VolatilityChangeFlag.INSUFFICIENT_HISTORY`
2. `REGIME_SHIFTING` if `volatility_direction in (VolatilityChangeFlag.RISING, VolatilityChangeFlag.FALLING)` **and** `volatility_regime in (VolatilityRegime.ELEVATED, VolatilityRegime.HIGH)`
3. `VOLATILITY_TRENDING` if `volatility_direction in (VolatilityChangeFlag.RISING, VolatilityChangeFlag.FALLING)` (any non-`INSUFFICIENT_HISTORY` regime that is not `ELEVATED` or `HIGH`)
4. `STABLE_REGIME` if `volatility_direction == VolatilityChangeFlag.STABLE`

This rule answers the charter question "is the series noisy, stable, or regime-changing?" by combining the upstream's two volatility classifications. It introduces no new dispersion rules and is fully deterministic.

### Confidence

`confidence` is determined by the following precedence (top-to-bottom; first match wins):

1. `INSUFFICIENT` if `risk_change_profile.history_points_used is None` **or** `risk_change_profile.history_points_used < 5`
2. `LOW` if `risk_change_profile.status == SummaryStatus.DEGRADED` **or** `risk_change_profile.status == SummaryStatus.MISSING_HISTORY` **or** `risk_change_profile.history_points_used < 20`
3. `MEDIUM` if `risk_change_profile.status == SummaryStatus.MISSING_COMPARE` **or** `risk_change_profile.history_points_used < 40` **or** `risk_change_profile.volatility_regime == VolatilityRegime.INSUFFICIENT_HISTORY`
4. `HIGH` otherwise (which implies all of: `risk_change_profile.status == SummaryStatus.OK`, `risk_change_profile.history_points_used >= 40`, `risk_change_profile.volatility_regime != VolatilityRegime.INSUFFICIENT_HISTORY`)

The numerical thresholds `5`, `20`, and `40` are point-count bands chosen relative to the PRD-1.1-v2 minimum-history rules (`rolling_std` requires ≥ 2; `volatility_regime` requires ≥ 20 valid points in the 60-business-day baseline). They are closed v1 conventions; any change requires a `walker_version` bump.

`SummaryStatus` values reachable inside a returned `RiskChangeProfile` per PRD-1.1-v2 are: `OK`, `DEGRADED`, `MISSING_COMPARE`, `MISSING_HISTORY`. The other `SummaryStatus` members (`PARTIAL`, `MISSING_NODE`, `MISSING_SNAPSHOT`, `UNSUPPORTED_MEASURE`) are out-of-band for this rule because they cannot appear inside a successfully returned `RiskChangeProfile` (per PRD-1.1-v2 status precedence). The walker treats any unexpected `SummaryStatus` value defensively by falling through to `LOW` if it does not satisfy the `OK` branch in step 4 — this is a defense-in-depth posture and must not be relied on as a contract.

### Caveat codes

`caveat_codes` is a deduplicated, lexicographically ascending tuple. The set is the union of all of the following condition-code mappings that evaluate true for the assessment:

| Condition | Caveat code |
| --- | --- |
| `risk_change_profile.status == SummaryStatus.DEGRADED` | `DEGRADED_UPSTREAM` |
| `outlier_flag == OutlierFlag.INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY_FOR_OUTLIER` |
| `trend_assessment == TrendAssessment.INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY_FOR_TREND` |
| `volatility_regime == VolatilityRegime.INSUFFICIENT_HISTORY` **or** `volatility_direction == VolatilityChangeFlag.INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY_FOR_VOLATILITY` |
| `risk_change_profile.status == SummaryStatus.MISSING_COMPARE` | `MISSING_COMPARE_POINT` |
| `risk_change_profile.status == SummaryStatus.MISSING_HISTORY` | `MISSING_HISTORY_WINDOW` |
| `risk_change_profile.rolling_std is not None` and `risk_change_profile.rolling_std == 0` | `ZERO_VARIANCE_BASELINE` |

If no condition is true, `caveat_codes = ()`. The walker introduces no orchestrator-style status precedence on caveats — every applicable caveat is emitted. Sorting is lexicographic ascending over the enum string values to keep the tuple deterministic and replay-stable.

The vocabulary is closed in v1. The walker does not propagate `risk_change_profile.status_reasons` into `caveat_codes` (the upstream `status_reasons` tuple remains accessible via the nested `risk_change_profile`; `caveat_codes` is a walker-owned classification surface, not an aggregator of upstream reason strings).

## Error handling

The walker propagates all error semantics from `get_risk_change_profile` unchanged.

**Returned typed `ServiceError` cases** (each carries `operation="get_risk_change_profile"`, a `status_code`, and `status_reasons`):

- `UNSUPPORTED_MEASURE` — propagated as-is, no `TimeSeriesAssessment` constructed
- `MISSING_SNAPSHOT` — propagated as-is, no `TimeSeriesAssessment` constructed
- `MISSING_NODE` — propagated as-is, no `TimeSeriesAssessment` constructed

**Raised `ValueError` cases** (request validation; propagated unchanged):

- `lookback_window` is not `60` (per PRD-1.1-v2 v1 constraint)
- `snapshot_id` is provided but blank
- `compare_to_date` is later than `as_of_date`

The walker adds no new error codes, no new error types, and no fallback behavior. In-object statuses (`OK`, `DEGRADED`, `MISSING_COMPARE`, `MISSING_HISTORY`) on a returned `RiskChangeProfile` are handled by the classification and caveat rules above; they do not become `ServiceError` outcomes at the walker layer.

The walker does not catch unexpected exceptions from `get_risk_change_profile`; any exception type other than `ValueError` (e.g., a future `TypeError` from contract drift) propagates unchanged.

## Replay and determinism

Aligned with ADR-002 (replay and snapshot model) and PRD-1.1-v2 `Replay requirements`:

- equal `(node_ref, measure_type, as_of_date, compare_to_date, lookback_window, require_complete, snapshot_id, fixture_index_state, walker_version, service_version, data_version)` inputs must produce equal `TimeSeriesAssessment` values, field-for-field, across runs
- `generated_at` is deterministic and equal to `risk_change_profile.generated_at`; the walker introduces no wall-clock dependency
- `walker_version` is pinned at module level (`time_series-v1.0.0` in this PRD slice) and bumped only by an explicit work item; any change to the classification thresholds, vocabulary members, precedence rules, or output schema requires a `walker_version` bump
- the walker does not introduce its own snapshot resolver, business-day primitive, or random source (ADR-004 and ADR-002 satisfied entirely by deferring to upstream)
- replay tests must demonstrate two-invocation field equality of `TimeSeriesAssessment` over a pinned upstream `RiskChangeProfile`

## Evidence and trace propagation

Aligned with ADR-003 (evidence and trace model) and PRD-1.1-v2 deferred-evidence-shape posture:

- `TimeSeriesAssessment.risk_change_profile` carries the upstream `RiskChangeProfile` unchanged, by reference (frozen nested model). All upstream replay metadata (`snapshot_id`, `data_version`, `service_version`, `generated_at`) and `status` / `status_reasons` are reachable via the nested object
- the walker must not strip, modify, supplement, or summarize any field on the nested `RiskChangeProfile`
- the walker does not introduce a new evidence shape, a new trace envelope, or a new correlation header in v1; PRD-1.1-v2's deferred-evidence-shape posture is honored
- `walker_version` and the walker's own `snapshot_id` (mirrored from upstream) serve as the walker-layer correlation surface in telemetry events

## Telemetry requirements

Aligned with `docs/shared_infra/telemetry.md`:

- the walker must use `src.shared.telemetry.emit_operation` for all structured operation events
- the walker must not import from `agent_runtime`
- the walker must not redefine status-to-level mapping (it is owned by the shared telemetry implementation)
- payload discipline: no raw fixtures, no full upstream typed objects, no `RiskChangeProfile` payloads in log records — only low-cardinality identifiers, counts, and canonical statuses
- `include_trace_context=False` in v1 (consistent with the `data_controller` walker emission pattern); a future WI may opt in to OpenTelemetry context propagation

### Required event (v1)

Exactly one event is emitted per `assess_time_series` call:

| Event `operation` | Status field source | Required context fields (in addition to `operation`, `status`, `duration_ms`) |
| --- | --- | --- |
| `assess_time_series` | when outcome is `TimeSeriesAssessment`: `risk_change_profile.status.value` (one of `OK`, `DEGRADED`, `MISSING_COMPARE`, `MISSING_HISTORY`); when outcome is `ServiceError`: `service_error.status_code` (one of `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`) | `node_ref` (via `node_ref_log_dict`), `measure_type`, `as_of_date`, `snapshot_id` (from request, may be `None`), `walker_version` |

The status mapping above is normative. Every value emitted in the `status` field must be one of the canonical statuses already supported by `_INFO_STATUSES` or `_WARNING_STATUSES` in `src.shared.telemetry.operation_log` (no new status strings introduced by this walker). The classification outcome enums (`trend_assessment`, `outlier_flag`, `regime_change_signal`, `volatility_regime`, `volatility_direction`, `regime_change_signal`, `confidence`) are deliberately **not** emitted as telemetry context fields in v1 — payload-discipline minimality first; a follow-on WI can add interpretive-outcome counters or histograms once orchestrator consumption patterns are stable.

### Adoption matrix

The `src/walkers/` row in `docs/shared_infra/adoption_matrix.md` is already `adopted` (Data Controller Walker, WI-4.1.4). When WI-4.3.4 lands, the row's `Notes` field must be extended to reflect Time Series Walker telemetry coverage (single-line note referencing WI-4.3.4 — no scope expansion).

## Acceptance criteria

### Functional

- Walker entry point `assess_time_series` exists and is importable as `from src.walkers.time_series import assess_time_series`
- `TimeSeriesAssessment` and the five supporting enums (`TrendAssessment`, `OutlierFlag`, `RegimeChangeSignal`, `TimeSeriesConfidence`, `TimeSeriesCaveatCode`) are importable from `src.walkers.time_series` (or its `contracts` submodule, exported via `__init__.py`)
- For any valid combination of inputs that yields a `RiskChangeProfile`, `assess_time_series(args)` returns a `TimeSeriesAssessment` whose:
  - mirrored fields equal the corresponding upstream fields exactly
  - `trend_assessment`, `outlier_flag`, `regime_change_signal`, `current_z_score`, `confidence`, and `caveat_codes` match the rules in `Classification vocabularies and inference rules`
  - `risk_change_profile` is the same `RiskChangeProfile` instance (by value equality) as the direct service call
  - `walker_version == "time_series-v1.0.0"`
- For each documented `ServiceError` path (`UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`), walker output equals direct service output
- For each documented `ValueError` validation path (invalid `lookback_window`, blank `snapshot_id`, `compare_to_date > as_of_date`), the walker raises the same `ValueError` (same message) that the service raises

### Contract

- Walker return type annotation is exactly `TimeSeriesAssessment | ServiceError` — no `Optional`, no additional union members, no wrapper around the wrapper
- `TimeSeriesAssessment` is a frozen pydantic model with `extra="forbid"`; all five enums are `StrEnum` with the exact members listed in this PRD; no extra members
- The mirrored-field invariants on `TimeSeriesAssessment` are enforced by validators and tested
- No imports of private service internals (only public module API and the established type submodule imports)
- No new types defined in the walker package beyond `TimeSeriesAssessment` and the five enums for v1
- Walker signature defaults exactly mirror `get_risk_change_profile` defaults
- `WALKER_VERSION` is a module-level string constant; not derived from environment or wall-clock

### Architecture

- Time-series classification rules and confidence rules live only in the walker package; no duplication of `risk_analytics` logic
- All deterministic statistics (rolling mean/std/min/max, volatility regime, volatility change flag, history-point counting) remain in `src/modules/risk_analytics/`; the walker reads them and classifies them but does not recompute them
- Walker package location is `src/walkers/time_series/` per `src/walkers/README.md` <!-- drift-ignore -->
- Package layout follows the established walker pattern (entry-point module + `contracts` module + `__init__.py` exporting public surfaces)
- No coupling to PRD-5.1 v1 orchestrator code; the orchestrator is named only as a future consumer
- No imports from `agent_runtime`; no direct imports of `src.modules.risk_analytics.service`; no imports from any other `src.walkers.*` package
- No coupling to `src.modules.controls_integrity.*` (the walker is independent of Data Controller Walker in v1)

### Replay

- Two-invocation determinism test: equal inputs across two invocations produce equal `TimeSeriesAssessment` instances (equal under pydantic model equality)
- `generated_at` equals `risk_change_profile.generated_at` (no wall-clock leakage)
- A pinned-upstream replay test constructs a known `RiskChangeProfile` and asserts the resulting `TimeSeriesAssessment` matches a pinned expected snapshot (field-for-field)

### Telemetry

- The `assess_time_series` event is emitted exactly once per call
- Payload contracts match the table in `Telemetry requirements`; no `RiskChangeProfile` or `ServiceError` payloads appear in log records
- `agent_runtime` is not imported transitively from the walker package
- `src/walkers/` row Notes in `docs/shared_infra/adoption_matrix.md` reflect Time Series Walker telemetry coverage after WI-4.3.4 lands

### Out of scope guarded

- No walker-owned `get_risk_history` call, business-day reasoning, raw-history-series exposure, narrative caveat prose, recommended-next-step prose, hierarchy localization, materiality rule, multi-target loop, multi-measure synthesis, second walker invocation, durable persistence, or trust-state gating from Data Controller appears in the v1 implementation

## Test intent

Tests must prove that the walker (a) is a faithful delegate of `get_risk_change_profile` for `ServiceError` and `ValueError` paths, and (b) produces deterministic, rule-correct interpretive output for every classification axis when the service returns a `RiskChangeProfile`.

### Parity tests (delegation correctness)

For each of the following cases, call both `assess_time_series` (walker) and `get_risk_change_profile` (service) with identical arguments. Assert the walker outcome category and equality:

| Case | Trigger | Expected walker outcome | Key assertion |
| --- | --- | --- | --- |
| Successful change profile | valid inputs, supported measure, `as_of_date` with snapshot, prior business day available | `TimeSeriesAssessment` | `walker.risk_change_profile == service_result` |
| Unsupported measure | `measure_type` not in fixture pack's `supported_measures` | `ServiceError(status_code="UNSUPPORTED_MEASURE")` | walker result `==` service result |
| Missing snapshot | `snapshot_id` does not exist | `ServiceError(status_code="MISSING_SNAPSHOT")` | walker result `==` service result |
| Missing node | snapshot exists but node not present | `ServiceError(status_code="MISSING_NODE")` | walker result `==` service result |
| Invalid `lookback_window` | `lookback_window != 60` | `ValueError` | walker raises same `ValueError` (same message) as service |
| Blank `snapshot_id` | `snapshot_id=""` | `ValueError` | walker raises same `ValueError` (same message) as service |
| `compare_to_date > as_of_date` | invalid compare-date input | `ValueError` | walker raises same `ValueError` (same message) as service |

### Classification truth-table tests

Construct `RiskChangeProfile` instances directly (or via fixtures) covering the matrix below and assert the resulting `TimeSeriesAssessment` field values. These tests need not call `get_risk_change_profile` — they can construct upstream typed objects in-test for full coverage of the rule space.

**Trend assessment matrix** (rolling_mean = 0, rolling_std = 1; vary current_value):

| `current_value` | Expected `current_z_score` | Expected `trend_assessment` | Expected `outlier_flag` |
| --- | --- | --- | --- |
| `3.5` | `3.5` | `EXTREME_ELEVATED_VS_BASELINE` | `EXTREME_OUTLIER` |
| `3.0` | `3.0` | `EXTREME_ELEVATED_VS_BASELINE` | `EXTREME_OUTLIER` |
| `2.5` | `2.5` | `ELEVATED_VS_BASELINE` | `OUTLIER` |
| `2.0` | `2.0` | `ELEVATED_VS_BASELINE` | `OUTLIER` |
| `1.5` | `1.5` | `ELEVATED_VS_BASELINE` | `NOT_OUTLIER` |
| `1.0` | `1.0` | `ELEVATED_VS_BASELINE` | `NOT_OUTLIER` |
| `0.5` | `0.5` | `NEAR_BASELINE` | `NOT_OUTLIER` |
| `0.0` | `0.0` | `NEAR_BASELINE` | `NOT_OUTLIER` |
| `-0.5` | `-0.5` | `NEAR_BASELINE` | `NOT_OUTLIER` |
| `-1.0` | `-1.0` | `SUPPRESSED_VS_BASELINE` | `NOT_OUTLIER` |
| `-2.0` | `-2.0` | `SUPPRESSED_VS_BASELINE` | `OUTLIER` |
| `-3.0` | `-3.0` | `EXTREME_SUPPRESSED_VS_BASELINE` | `EXTREME_OUTLIER` |

**Insufficient-history fallthrough**:

| Upstream condition | Expected `current_z_score` | Expected `trend_assessment` | Expected `outlier_flag` |
| --- | --- | --- | --- |
| `rolling_std is None` | `None` | `INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY` |
| `rolling_mean is None` | `None` | `INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY` |
| `rolling_std == 0` | `None` | `INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY` |

**Regime-change signal matrix**:

| `volatility_regime` | `volatility_change_flag` | Expected `regime_change_signal` |
| --- | --- | --- |
| `LOW` | `STABLE` | `STABLE_REGIME` |
| `LOW` | `RISING` | `VOLATILITY_TRENDING` |
| `LOW` | `FALLING` | `VOLATILITY_TRENDING` |
| `NORMAL` | `STABLE` | `STABLE_REGIME` |
| `NORMAL` | `RISING` | `VOLATILITY_TRENDING` |
| `ELEVATED` | `STABLE` | `STABLE_REGIME` |
| `ELEVATED` | `RISING` | `REGIME_SHIFTING` |
| `ELEVATED` | `FALLING` | `REGIME_SHIFTING` |
| `HIGH` | `STABLE` | `STABLE_REGIME` |
| `HIGH` | `RISING` | `REGIME_SHIFTING` |
| `HIGH` | `FALLING` | `REGIME_SHIFTING` |
| `INSUFFICIENT_HISTORY` | any | `INSUFFICIENT_HISTORY` |
| any | `INSUFFICIENT_HISTORY` | `INSUFFICIENT_HISTORY` |

**Confidence matrix** (subset; coding agent should test every precedence transition):

| Upstream `status` | `history_points_used` | `volatility_regime` | Expected `confidence` |
| --- | --- | --- | --- |
| `OK` | `60` | `NORMAL` | `HIGH` |
| `OK` | `40` | `NORMAL` | `HIGH` |
| `OK` | `39` | `NORMAL` | `MEDIUM` |
| `OK` | `40` | `INSUFFICIENT_HISTORY` | `MEDIUM` |
| `OK` | `20` | `NORMAL` | `MEDIUM` |
| `OK` | `19` | `NORMAL` | `LOW` |
| `OK` | `5` | `NORMAL` | `LOW` |
| `OK` | `4` | `NORMAL` | `INSUFFICIENT` |
| `OK` | `None` | `NORMAL` | `INSUFFICIENT` |
| `MISSING_COMPARE` | `60` | `NORMAL` | `MEDIUM` |
| `MISSING_HISTORY` | `60` | `NORMAL` | `LOW` |
| `DEGRADED` | `60` | `NORMAL` | `LOW` |

**Caveat-code matrix** (subset; coding agent should test each condition independently and at least one combined case):

| Upstream condition | Expected `caveat_codes` (sorted) |
| --- | --- |
| clean `OK`, `history_points_used=60`, `rolling_std > 0`, no `INSUFFICIENT_HISTORY` | `()` |
| `status=DEGRADED`, otherwise clean | `("DEGRADED_UPSTREAM",)` |
| `volatility_regime=INSUFFICIENT_HISTORY`, otherwise clean | `("INSUFFICIENT_HISTORY_FOR_VOLATILITY",)` |
| `rolling_std=0`, `rolling_mean=0`, current=0 | `("INSUFFICIENT_HISTORY_FOR_OUTLIER", "INSUFFICIENT_HISTORY_FOR_TREND", "ZERO_VARIANCE_BASELINE")` |
| `status=MISSING_COMPARE` | `("MISSING_COMPARE_POINT",)` |
| `status=MISSING_HISTORY` | `("MISSING_HISTORY_WINDOW",)` |
| combined: `status=DEGRADED` and `volatility_regime=INSUFFICIENT_HISTORY` | `("DEGRADED_UPSTREAM", "INSUFFICIENT_HISTORY_FOR_VOLATILITY")` (sorted) |

### Replay tests

- Two-invocation determinism over `get_risk_change_profile` (using a pinned fixture index): `assess_time_series(args) == assess_time_series(args)`
- Pinned-upstream determinism: construct a known `RiskChangeProfile` directly (bypassing the service) and assert `assess_time_series` produces a known expected `TimeSeriesAssessment` via a `model_dump()` snapshot or full field-by-field comparison

### Telemetry tests

- caplog-style assertion that the `assess_time_series` event is emitted exactly once per call with the documented context fields
- assertion that no `RiskChangeProfile` or `ServiceError` payload leaks into log records (only low-cardinality fields)
- assertion that `agent_runtime` is not imported transitively from the walker package

### Mirrored-field invariant tests

- Constructing a `TimeSeriesAssessment` with any mirrored field that disagrees with the nested `risk_change_profile` raises `ValueError`
- Constructing a `TimeSeriesAssessment` with empty `walker_version` raises `ValueError`

If any required combination is unreachable with current `risk_analytics` fixtures, the coding agent must cover the maximal subset reachable with existing fixtures and exercise the remainder by constructing `RiskChangeProfile` instances directly in-test (the contract-level tests do not require service-side fixtures).

## Downstream consumer contract

This section is normative for downstream PRD authors (PRD-5.1-v2 multi-walker orchestration; Governance / Reporting Walker v1, post-MVP near-term).

### What PRD-5.1-v2 will consume

A future PRD-5.1-v2 multi-walker routing slice can rely on the following stable surface from this walker without further negotiation:

- **Entry point**: `assess_time_series(node_ref, measure_type, as_of_date, compare_to_date=None, lookback_window=60, require_complete=False, snapshot_id=None, fixture_index=None) -> TimeSeriesAssessment | ServiceError`
- **Outcome union**: identical structural shape to `summarize_change` (PRD-4.2) at the union level — wrapped success type or unchanged `ServiceError` — so PRD-5.1-v2 can implement uniform per-walker outcome handling
- **Routing-relevant fields**: PRD-5.1-v2 routing logic may safely read any of:
  - `confidence` — consumers should expect `INSUFFICIENT` to indicate the assessment is unreliable for governance and may choose to skip narrative inclusion
  - `caveat_codes` — closed v1 vocabulary; consumers may map specific codes to per-target handoff caveats following the `TargetHandoffEntry` pattern from PRD-5.1
  - `trend_assessment`, `outlier_flag`, `regime_change_signal` — closed v1 vocabularies suitable for routing decisions ("if `outlier_flag in (OUTLIER, EXTREME_OUTLIER)` route to Critic / Challenge Walker", etc.)
  - `current_z_score` — `float | None`; consumers must handle `None` explicitly
- **Replay metadata**: consumers should treat `walker_version` as part of the replay context and propagate it into orchestrator-level telemetry and run identifiers; `snapshot_id`, `data_version`, `service_version`, and `generated_at` are reachable via the nested `risk_change_profile` and align with the upstream-service replay context
- **Trust-gate boundary**: PRD-5.1-v2 owns the decision of whether to call `assess_time_series` based on Data Controller trust state. The walker itself does not consult or require `IntegrityAssessment`. PRD-5.1-v2's per-target routing rule may therefore be expressed as: "for each `selected_targets` entry whose Data Controller `trust_state` permits analytical interpretation, call `assess_time_series`"

### What PRD-5.1-v2 must not assume

- The walker does not return `None`, raise on a `ServiceError`, or wrap the outcome in any orchestrator-style envelope; consumers must handle the `TimeSeriesAssessment | ServiceError` union directly
- The walker does not emit narrative text; any narrative belongs to the Governance / Reporting Walker (post-MVP near-term)
- The walker does not expose `RiskHistorySeries` raw points; consumers needing them must call `get_risk_history` directly
- The walker enums are closed v1 vocabularies; consumers should not assume forward extension and should fail closed (e.g., raise on unknown enum values) if forward compatibility is not contracted in a future PRD update
- The walker does not propagate or aggregate cross-target context; PRD-5.1-v2 is responsible for any per-run aggregation

### What the Governance / Reporting Walker v1 PRD will consume

The Governance / Reporting Walker v1 PRD (DECISION-MVP-02 deferral; to be authored after this PRD is in draft) can rely on `TimeSeriesAssessment` as the canonical typed input from the time-series interpretive layer. It will read:

- `trend_assessment`, `outlier_flag`, `regime_change_signal`, `volatility_regime`, `volatility_direction`, `confidence`, `caveat_codes` for narrative synthesis vocabulary
- `current_z_score` and `risk_change_profile` (nested) for evidence and quantitative context
- `walker_version`, `snapshot_id`, `generated_at` for replay metadata propagation into governance packs

The Governance Walker v1 PRD must not require this walker to author free-text narrative or recommended-next-step prose; all such synthesis is the Governance Walker's responsibility.

## Issue decomposition guidance

This PRD is implemented by four bounded work items. The PM / Issue Planner derives concrete WIs from this guidance.

### Suggested sequence

1. **WI-4.3.1 — Time Series Walker v1 implementation PRD** (this document; mirrors WI-4.1.1 and WI-4.2.1 pattern)
   - depends on: PRD-1.1-v2 (already merged), PRD-4.1 (already merged), PRD-4.2 (already merged)
   - shared-infra impact: declared but not yet adopted (telemetry slice is WI-4.3.4)

2. **WI-4.3.2 — Walker package skeleton and typed contracts**
   - create `src/walkers/time_series/` package with `__init__.py` exporting the public surface (mirroring `src/walkers/data_controller/__init__.py` and `src/walkers/quant/__init__.py`) <!-- drift-ignore -->
   - define `TimeSeriesAssessment` and the five `StrEnum` vocabularies (`TrendAssessment`, `OutlierFlag`, `RegimeChangeSignal`, `TimeSeriesConfidence`, `TimeSeriesCaveatCode`) in a `contracts.py` (or `contracts/` package) module
   - pin `WALKER_VERSION = "time_series-v1.0.0"` at module level
   - define the `assess_time_series` entry-point signature only (raise `NotImplementedError` body); no classification or service call yet
   - unit tests for typed-model construction, mirrored-field invariants, and enum membership
   - depends on: WI-4.3.1 merged on `main`

3. **WI-4.3.3 — Entry-point implementation and classification logic**
   - implement `assess_time_series` per this PRD: call `get_risk_change_profile`, propagate `ServiceError`, construct `TimeSeriesAssessment` via the classification rules
   - implement z-score derivation, trend / outlier / regime-change classification, confidence rule, and caveat-code rule
   - parity tests (delegation correctness) and classification truth-table tests per `Test intent`
   - replay-determinism tests (two-invocation equality and pinned-upstream snapshot)
   - mirrored-field invariant tests
   - depends on: WI-4.3.2
   - no telemetry yet (added in WI-4.3.4)

4. **WI-4.3.4 — Telemetry adoption + adoption-matrix note extension**
   - add `emit_operation` call in `assess_time_series` per the telemetry table; status mapping per the rules above
   - assert payload discipline (no `RiskChangeProfile` payloads in logs; only low-cardinality fields)
   - extend `docs/shared_infra/adoption_matrix.md` `src/walkers/` row Notes to mention Time Series Walker telemetry coverage with WI-4.3.4 reference (single-line note; no scope expansion)
   - telemetry tests per `Test intent`
   - depends on: WI-4.3.3

### Sequencing notes for PM

- WI-4.3.2 and WI-4.3.3 may be merged into a single WI if PM/Issue Planner judges them small enough; in that case the typed contracts must land first within the combined slice (mirroring PRD-5.1's WI-5.1.1 vs WI-5.1.2 guidance)
- WI-4.3.4 is the gate for the adoption-matrix Notes update; it must not be merged until telemetry payload tests pass
- this PRD can be authored and decomposed in parallel with PRD-4.2-v2 (Quant Walker interpretive output) because the upstream contract dependencies are already stable on `main` and the two walkers do not share output types
- no WI in this sequence is permitted to widen scope beyond this PRD; any expansion (`get_risk_history` integration, raw-history-series exposure, narrative caveats, multi-target invocation, second walker dependency, Data Controller trust-gate consumption inside the walker, hierarchy fan-out) requires a new PRD or a v2 PRD update

### Out of decomposition (will not be issued under this PRD)

- `get_risk_history` integration / raw-series exposure (v2+ Open Question)
- Narrative caveat prose, recommended-next-step prose, hierarchy localization
- Multi-target / multi-measure / batch invocation
- Trust-gate consumption from Data Controller Walker output (orchestrator concern in PRD-5.1-v2)
- Data Controller Walker fixtures or any controls-integrity coupling
- Live-data integration (post-MVP per DECISION-MVP-01)
- Governance pack assembly (covered by future Governance / Reporting Walker v1 PRD; post-MVP near-term per DECISION-MVP-02)

## Open questions (v2+ only — none block v1)

- **`get_risk_history` integration and raw-series exposure.** v1 delegates to `get_risk_change_profile` only. A v2+ revision could add a second upstream call to `get_risk_history` and an optional `history_series: RiskHistorySeries | None` field on `TimeSeriesAssessment` if a concrete consumer (e.g., Presentation / Visualization Walker) requires the raw points via this walker's surface. The decision should be driven by a concrete downstream requirement and must address the ADR-004 business-day-alignment concern (see `Why get_risk_change_profile only` rationale).
- **Trust-gate coupling with Data Controller Walker.** v1 is independent of `IntegrityAssessment`. A future v2+ revision could choose to either (a) consume `IntegrityAssessment` as an explicit input (fail-fast on `BLOCKED`/`UNRESOLVED` trust state) or (b) leave that decision permanently in the orchestrator. The PRD-5.1-v2 routing design will clarify which is preferable; if the orchestrator owns the gate, the walker stays as designed.
- **Threshold tuning.** The numerical thresholds (`1.0` / `3.0` for trend; `2.0` / `3.0` for outlier; `5` / `20` / `40` for confidence point counts) are closed v1 conventions. Methodology calibration against historical fixtures, FRTB conventions, or a quantitative review may revise them; any change requires a `walker_version` bump per the version-discipline rule.
- **Series-level outlier scan.** The current outlier flag classifies the **current point** only. A v2+ revision could add a `historical_outliers: tuple[date, ...]` field listing points within the lookback window whose z-score exceeds a threshold. Requires `get_risk_history` integration first.
- **Telemetry of interpretive outcomes.** The `assess_time_series` event in v1 emits only minimal context. A future telemetry slice could add `trend_assessment`, `confidence`, and `caveat_codes_count` as low-cardinality counters or labels. Requires adoption matrix coordination and follow-on shared-telemetry design (e.g., metrics adapters per `docs/shared_infra/telemetry.md` recommended layout).
- **Narrative caveats.** The `caveat_codes` vocabulary is structured and closed. Free-text narrative caveats remain a Governance / Reporting Walker concern (post-MVP near-term). If a downstream consumer requires walker-authored prose, a v2+ PRD must add it explicitly with a new field and associated typed contract.
- **Walker-emitted recommended-next-step.** The walker does not emit recommended next steps. Whether to add a structured `recommended_next_step: NextStep | None` field tied to a closed vocabulary (e.g., `INVESTIGATE_OUTLIER`, `MONITOR_REGIME_SHIFT`, `NO_ACTION`) is a v2+ design choice with downstream-routing implications; defer until orchestrator / governance consumption patterns are clearer.
- **Time Series Walker exemplar alignment.** No exemplar exists at `docs/prd_exemplars/PRD-4.3-time-series-walker.md`. If one is authored, this PRD should be reviewed for alignment before any v2+ behavior is added. The exemplar must be treated as non-normative for v1 unless and until a future PRD update adopts it.

## Reviewer checklist

- v1 includes interpretive output as Module 1 MVP requires; the `Why this is the v1 slice (delegation-only vs interpretive)` section makes the decision explicit with rationale
- Walker delegates to exactly one upstream service function (`get_risk_change_profile`); `get_risk_history`, `get_risk_summary`, and `get_risk_delta` are explicitly out of scope and recorded as Open Questions
- PRD-1.1-v2 semantics (status precedence, delta-field rules, volatility-rules-v1, replay/version metadata) are cross-referenced, not restated or altered
- Walker is independent of Data Controller Walker output; trust-gate routing belongs to PRD-5.1-v2 and is not embedded in the walker
- Output type is `TimeSeriesAssessment | ServiceError`; the wrapper has no walker-authored narrative, recommended-next-step prose, evidence-shape, or trace-context envelope; no second wrapper type
- All five enum vocabularies are closed in v1 with the exact members listed; thresholds (`1.0`, `2.0`, `3.0`, `5`, `20`, `40`) are explicit; precedence rules are top-to-bottom first-match
- Mirrored-field invariants on `TimeSeriesAssessment` are enforced by validators and tested
- `walker_version` is pinned at module level; `generated_at` equals `risk_change_profile.generated_at`; no wall-clock leakage
- Import rules restrict the walker to public `risk_analytics` API plus established type submodule imports; no `agent_runtime`, no private service helpers, no controls-integrity coupling, no other walker package imports
- Error handling is pass-through: `ServiceError` and `ValueError` propagate unchanged with no walker-introduced fallback or re-wrap
- Telemetry uses `src.shared.telemetry.emit_operation` exclusively; no module-local status mapping; no `RiskChangeProfile` payloads in log records; only low-cardinality context fields
- Adoption matrix `src/walkers/` row Notes are extended to reflect Time Series Walker telemetry coverage when WI-4.3.4 lands (no row status change required since `src/walkers/` is already `adopted`)
- Acceptance criteria, classification truth-table tests, parity tests, and replay tests are sufficient for WI-4.3.2 / WI-4.3.3 / WI-4.3.4 coding without guesswork
- No new ADR-level concept, no new shared-infra contract, no schema change to PRD-1.1-v2 contracts has leaked in
- Backtick-wrapped repository paths in this PRD either exist on `main` (`src/modules/risk_analytics/`, `src/modules/risk_analytics/contracts/`, `src/modules/risk_analytics/fixtures/`, `src/walkers/data_controller/`, `src/walkers/quant/`, `src/walkers/README.md`, `src/shared/`, `src/shared/telemetry/`, all `docs/...` paths) or are explicitly called out as planned with a linked work item in the header (`src/walkers/time_series/` — created by WI-4.3.2), consistent with reference-integrity and registry-alignment checks
- Out-of-scope items have not silently leaked into v1 (`get_risk_history`, raw-series exposure, narrative prose, recommended-next-step, hierarchy localization, multi-target loop, multi-measure synthesis, Data Controller trust gate inside the walker, materiality logic, live-data integration, durable persistence, governance pack assembly)
- Downstream consumer contract section is unambiguous enough that PRD-5.1-v2 and the future Governance / Reporting Walker v1 PRD authors can specify their inputs against this walker's surface without further negotiation

## AI agent instructions

### Coding agent

- implement exactly what this PRD specifies; do not add fields, enum members, classification axes, walker-authored narrative, recommended-next-step prose, additional upstream calls, or trust-gate logic not listed here
- consume `RiskChangeProfile | ServiceError` only via the public `src.modules.risk_analytics.get_risk_change_profile` surface; do not import private service helpers or classifier internals
- do not call `get_risk_history`, `get_risk_summary`, or `get_risk_delta`; the walker uses one upstream function in v1
- do not import from `src.modules.controls_integrity.*` or any other walker package
- use `src.shared.telemetry.emit_operation` exactly per the telemetry table; do not invent new status strings; do not include `RiskChangeProfile` payloads in log records
- pin `WALKER_VERSION = "time_series-v1.0.0"` at module level; do not derive it from environment, wall-clock, or git state
- enforce mirrored-field invariants on `TimeSeriesAssessment` via pydantic validators (raise `ValueError` on mismatch)
- if any test reveals an ambiguity in the PRD, stop and route the question back through PM / PRD; do not invent semantics

### Review agent

- check that the walker delegates to exactly one upstream function (`get_risk_change_profile`) and does not call `get_risk_history`, `get_risk_summary`, or `get_risk_delta`
- check that all classification outputs follow the precedence rules in this PRD with no walker-introduced thresholds beyond those listed
- check that `RiskChangeProfile` and `ServiceError` are propagated unchanged (the walker may inspect `RiskChangeProfile` typed fields for classification but must not modify or substitute any field)
- check that no walker-authored narrative, recommended-next-step prose, evidence-shape, or trace-context envelope appears
- check that mirrored-field invariants on `TimeSeriesAssessment` are enforced and tested
- check telemetry payload discipline (no `RiskChangeProfile` in log records) and adoption-matrix Notes extension
- check that `agent_runtime` is not imported transitively from the walker package
- check that `WALKER_VERSION` is pinned at module level and that classification thresholds match this PRD exactly
- flag any scope creep (additional upstream call, raw-history-series exposure, narrative caveat prose, recommended-next-step, multi-target loop, Data Controller trust-gate consumption, materiality rule) explicitly as out of scope

### PM agent

- treat WI-4.3.1, WI-4.3.2, WI-4.3.3, and WI-4.3.4 as the bounded sequence under this PRD
- do not assign any WI under this PRD that widens scope beyond the in-scope list
- the adoption-matrix Notes extension (WI-4.3.4) is part of v1 acceptance and must not be deferred
- this PRD's downstream consumer contract is the canonical input surface for the next PRD-5.1-v2 author and the future Governance / Reporting Walker v1 author; treat it as a stable contract for parallel PRD work

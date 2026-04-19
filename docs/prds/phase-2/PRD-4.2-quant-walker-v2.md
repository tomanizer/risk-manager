# PRD-4.2-v2: Quant Walker v2 — Interpretive Output

## Header

- **PRD ID:** PRD-4.2-v2
- **Title:** Quant Walker v2 — Interpretive Output Over `RiskChangeProfile`
- **Phase:** Phase 2
- **Status:** Ready for implementation
- **Layer:** Walker
- **Type:** Interpretive walker (typed wrapper output over deterministic upstream)
- **Primary owner:** Technical Owner, Quant Walker
- **Supersedes:** `archive/PRD-4.2-quant-walker-v1-archived.md` for implementation planning; v2 extends the delegate-only v1 contract (historical record: WI-4.2.2, PR #168) and closes its Open Questions required for Module 1 MVP.
- **Upstream service PRD:** PRD-1.1-v2 (Risk Summary Service v2) — typed outputs the walker interprets
- **Sibling walker reference (pattern only):** PRD-4.1 (Data Controller Walker v1) — same `src/walkers/` package layout and telemetry pattern
- **Downstream consumer (gated by this PRD):** PRD-5.1-v2 (Daily Risk Investigation Orchestrator multi-walker routing) — orchestrator routing and synthesis depend on the typed output named in this PRD
- **Downstream consumer (post-MVP, near-term):** Governance / Reporting Walker v1 PRD — deferred until Quant v2 and Time Series v1 typed outputs are contracted (per closed decision DECISION-MVP-02 in `docs/roadmap/module_1_var_dashboard.md`)
- **Related ADRs:** ADR-001 (schema and typing), ADR-002 (replay and snapshot model), ADR-003 (evidence and trace model)
- **Related shared infra:** `docs/shared_infra/index.md`, `docs/shared_infra/adoption_matrix.md`, `docs/shared_infra/telemetry.md`
- **Related charters:** `docs/05_walker_charters.md` (Quant Walker — mission, core questions, confidence model)
- **Related closed decisions:** DECISION-MVP-01 (live-data integration is post-MVP), DECISION-MVP-02 (Governance / Reporting Walker is post-MVP) — both in `docs/roadmap/module_1_var_dashboard.md`
- **Related components (existing on `main`):**
  - `src/modules/risk_analytics/` (deterministic service)
  - `src/modules/risk_analytics/contracts/` (typed contracts: `RiskChangeProfile`, `MeasureType`, `NodeRef`, `VolatilityRegime`, `VolatilityChangeFlag`, `SummaryStatus`)
  - `src/modules/risk_analytics/fixtures/` (fixture index)
  - `src/walkers/quant/` (v1 delegate package merged via WI-4.2.2)
  - `src/walkers/data_controller/` (sibling walker pattern reference)
  - `src/walkers/README.md` (walker package conventions)
  - `src/shared/` (`ServiceError`, `EvidenceRef`)
  - `src/shared/telemetry/` (`emit_operation`, `node_ref_log_dict`, `timer_start`)
- **Exemplar:** none. No docs/prd_exemplars/PRD-4.2-quant-walker.md exists; alignment with any future Quant Walker exemplar remains an Open Question.

## Purpose

Extend the Quant Walker from a delegation-only facade (PRD-4.2 v1) into an interpretive walker that produces typed, replay-safe, governed inferences over the deterministic risk-change output it already receives from `risk_analytics.get_risk_change_profile`.

Walker v2 answers the Quant Walker charter's core questions (`docs/05_walker_charters.md`):

- **what changed quantitatively?** — propagated from upstream `RiskChangeProfile`
- **how large is the movement?** — emitted as a typed `significance` field with deterministic inference rules
- **is the change first-order movement, second-order instability, or both?** — emitted as a typed `change_kind` field with deterministic inference rules
- **how confident is the answer?** — emitted as a typed `confidence` field with deterministic inference rules

Walker v2 does **not** introduce new quantitative semantics. All deterministic risk semantics — first-order delta construction, rolling statistics, volatility regime classification, volatility change-flag classification, status precedence, replay/version metadata — remain in `src/modules/risk_analytics/` as governed by PRD-1.1-v2. The walker reads those typed fields and synthesizes interpretive output over them.

## Why this is the v2 slice

The v1 delegate boundary is now established and tested on `main` (WI-4.2.2). Per Module 1 MVP definition (`docs/roadmap/module_1_var_dashboard.md`), Module 1 MVP requires actual walker inference over the deterministic risk change output, not bare delegation. The current Quant Walker capability state is `delegate_only`, and the dashboard names "Quant Walker v2 contract is not yet defined" as the first MVP blocker.

PRD-4.2-v2 is also a critical-path blocker for two downstream PRDs:

1. **PRD-5.1-v2 (multi-walker orchestration)** — the orchestrator must name the concrete Quant Walker v2 output type to specify routing and per-target synthesis. Without that contract, PRD-5.1-v2 cannot specify how to consume Quant Walker output.
2. **Governance / Reporting Walker v1 PRD** (post-MVP, near-term per DECISION-MVP-02) — deferred precisely until Quant v2 and Time Series v1 output types are contracted.

This PRD closes every Open Question from PRD-4.2 v1 that is required for Module 1 MVP, defines the typed downstream contract that PRD-5.1-v2 will reference verbatim, and provides issue decomposition guidance for the Issue Planner.

## In scope

- Extend the existing `src/walkers/quant/` package (created by WI-4.2.2) with interpretive logic. The `summarize_change` entry point is retained as the single public function but its return type is widened from `RiskChangeProfile | ServiceError` (v1) to `QuantInterpretation | ServiceError` (v2). See "Walker contract" for the full signature.
- New typed contract module under `src/walkers/quant/` defining `QuantInterpretation`, `ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode`, and `InvestigationHint`. All types are frozen Pydantic models / `StrEnum` per ADR-001 and the existing pattern in `src/modules/risk_analytics/contracts/`.
- Deterministic inference rules over the typed fields already present in `RiskChangeProfile`, fully specified in this PRD (no rule decisions pushed to coding).
- Telemetry adoption for the Quant Walker package via `src.shared.telemetry.emit_operation`, mirroring the `data_controller` walker pattern. Adoption-matrix update for the `src/walkers/` row to reflect Quant Walker coverage.
- Replay-safe behavior: every interpretive field is deterministically derivable from the typed inputs and the upstream typed `RiskChangeProfile` alone. No wall-clock dependency. No external state.
- Unit and replay tests covering: typed contract construction, every documented inference-rule branch over the typed input space, telemetry payload shape, and replay equality (same upstream `RiskChangeProfile` produces an equal `QuantInterpretation`).

## Out of scope

- Any change to PRD-1.1-v2 service semantics, status precedence, delta-field rules, volatility-rules-v1, replay/version metadata, or fixture surface
- Any new ADR-level concept; no new shared-infra contract; no new typed status vocabulary on the upstream service; no new error envelope (`ServiceError` is reused unchanged)
- Hierarchy localization as a walker-emitted output (deferred to v3 per "Hierarchy localization decision" below)
- Multi-target invocation, batch invocation, multi-measure synthesis, hierarchy fan-out (single-target, single-measure only — these are orchestrator concerns)
- Multi-function delegation: v2 does **not** add `summarize_summary`, `summarize_delta`, or `summarize_history` walker entry points (deferred to v3 per "Multi-function delegation decision" below; PRD-5.1-v2 has no documented requirement for them)
- Free-text findings, narrative caveats, recommended-next-step prose, walker-authored human-readable summary text (interpretive output is fully typed; investigation hints are a typed enum, not prose)
- Cross-walker integration: no Time Series Walker, Market Context Walker, Critic / Challenge Walker, Controls / Change Walker, Model Risk & Usage Walker, Governance / Reporting Walker coupling. The orchestrator (PRD-5.1-v2) owns inter-walker routing.
- UI rendering, analyst review console, dashboard surfaces, governance sign-off, human escalation flows
- Live-data integration (post-MVP per DECISION-MVP-01); MVP is fixture-backed, operator-invoked
- Durable persistence of walker output (orchestrator owns return-by-value handoff per PRD-5.1)
- Automatic reasoning over `get_risk_summary`, `get_risk_delta`, or `get_risk_history` outputs from inside the walker (those data sources are accessible via direct service calls; the walker reads them only through `get_risk_change_profile`, which already aggregates first-order and second-order context)
- FRTB / PLA / HPL / RTPL stages, model-risk-usage walker concerns, regulatory-capital interpretation
- Any inference rule that depends on data sources outside the public `risk_analytics` API surface

## Users and consumers

Primary consumers of `summarize_change` returning `QuantInterpretation | ServiceError`:

- **Daily Risk Investigation Orchestrator v2** (PRD-5.1-v2, in flight). Orchestrator invokes `summarize_change` per selected target after the readiness gate and trust-state check. The orchestrator must propagate `QuantInterpretation` by reference into its per-target synthesis output (no transformation; per ADR-003 evidence model). See "Downstream consumer contract" for the binding shape.
- **Governance / Reporting Walker v1** (post-MVP, near-term). Consumes the typed `change_kind`, `significance`, `confidence`, and `investigation_hints` fields to assemble governance-ready output. Walker-to-walker coupling occurs via the orchestrator, not directly.
- **Replay harness** (existing). Verifies determinism: equal upstream `RiskChangeProfile` produces an equal `QuantInterpretation`.

Secondary consumers (read-only):

- Analyst review console (post-MVP)
- Drift Monitor and other governance audit surfaces (typed output is auditable per ADR-001 / ADR-003)

The walker introduces exactly one new typed object (`QuantInterpretation`) and four new typed enums for consumers to handle. No existing consumer of the v1 `RiskChangeProfile | ServiceError` union is broken by v2: the upstream `RiskChangeProfile` is preserved verbatim inside `QuantInterpretation.risk_change_profile`. Direct callers of `risk_analytics.get_risk_change_profile` are unaffected (the upstream service contract is unchanged).

## Walker contract

### Public entry point

The walker exposes one public function. The function name is preserved from v1 to keep the boundary stable for direct importers; the return type widens.

**Function name:** `summarize_change`

**Location:** `src/walkers/quant/walker.py`, exported via `src/walkers/quant/__init__.py` as `from src.walkers.quant import summarize_change`.

**Signature (v2):**

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
) -> QuantInterpretation | ServiceError:
```

The signature parameters and defaults mirror `get_risk_change_profile` exactly, as in v1. Any future change to the upstream service defaults must be reflected here in lockstep — the walker still does not pin or override defaults.

**Behavior (v2):** the walker calls `get_risk_change_profile` with the same arguments unchanged, then:

- if the upstream returns a `ServiceError`, the walker propagates it unchanged. No `QuantInterpretation` is constructed (the walker never fabricates interpretive fields without an underlying `RiskChangeProfile`).
- if the upstream returns a `RiskChangeProfile`, the walker constructs a frozen `QuantInterpretation` whose interpretive fields are computed deterministically per the rules in "Classification vocabularies and inference rules", with the upstream `RiskChangeProfile` propagated by reference into the `risk_change_profile` field.
- the walker emits exactly one structured operation event via `src.shared.telemetry.emit_operation` (see "Telemetry requirements").

The walker must not mutate, reshape, or re-derive any field on `RiskChangeProfile`. The upstream object is propagated by nested reference (immutable per its `frozen=True` config).

### Output type — `QuantInterpretation`

Defined in src/walkers/quant/contracts.py (new module created by the typed-contracts WI; see "Issue decomposition guidance"; path is the planned WI-4.2.4 deliverable, not yet on `main`). Frozen Pydantic model with `extra="forbid"`, consistent with `_RiskContractBase` in `src/modules/risk_analytics/contracts/summary.py` and ADR-001.

Fields (ordered as the model should declare them):

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_change_profile` | `RiskChangeProfile` | yes | Upstream typed object, propagated by reference unchanged. Source of truth for all replay/version metadata, status, and quantitative fields. |
| `change_kind` | `ChangeKind` | yes | Walker classification of the movement nature. See `ChangeKind` vocabulary and inference rule. |
| `significance` | `SignificanceLevel` | yes | Walker assessment of how large the movement is. See `SignificanceLevel` vocabulary and inference rule. |
| `confidence` | `ConfidenceLevel` | yes | Walker confidence in this interpretation. See `ConfidenceLevel` vocabulary and inference rule. |
| `caveats` | `tuple[QuantCaveatCode, ...]` | yes (may be empty) | Typed caveat codes derived deterministically from upstream typed fields. Order: lexicographic ascending. Deduplicated. See `QuantCaveatCode` vocabulary and inference rule. |
| `investigation_hints` | `tuple[InvestigationHint, ...]` | yes (may be empty) | Typed pointers indicating which downstream walker(s) or data dimension(s) deserve deeper investigation. Order: lexicographic ascending. Deduplicated. See `InvestigationHint` vocabulary and inference rule. |
| `walker_version` | `str` | yes | Pinned at module level in `src/walkers/quant/walker.py` (e.g., `QUANT_WALKER_VERSION = "v2.0.0"`). Bumped only by an explicit work item; any change to this PRD's typed contracts, vocabularies, or inference rules requires a version bump. |

**Replay metadata:** `QuantInterpretation` does **not** duplicate `snapshot_id`, `data_version`, `service_version`, or `generated_at` at the top level. Those fields are accessed via `risk_change_profile.snapshot_id`, etc. The walker introduces one new pinned identifier — `walker_version` — analogous to `orchestrator_version` in PRD-5.1. This avoids parallel evidence surfaces (per ADR-003 — "structured evidence references must travel with governed outputs, not be replicated as parallel narrative") and keeps a single source of truth for upstream version metadata.

**Evidence references:** v2 does not introduce a separate `evidence_refs: tuple[EvidenceRef, ...]` field on `QuantInterpretation`. The upstream `RiskChangeProfile` is itself the structured evidence carrier (per ADR-003: "typed outputs and replay artifacts remain the canonical evidence surfaces"). Adding a separate `evidence_refs` field on `QuantInterpretation` would create duplicate evidence surfaces with no new typed pointer source. If a future v3+ slice introduces walker-emitted external evidence (e.g., references to time-series outputs synthesized at the orchestrator level), `EvidenceRef` from `src.shared` is the canonical shape to use.

**No additional fields** in v2: no `walker_metadata`, no `walker_trace`, no free-text `summary`, no `recommended_next_step`, no `description`, no `narrative`. All interpretive content is typed.

### Output type — error path

When `get_risk_change_profile` returns a `ServiceError`, `summarize_change` returns the same `ServiceError` instance unchanged. The walker does not wrap the error, does not introduce a new error envelope, and does not synthesize a `QuantInterpretation` with degraded fields in lieu of an error. This rule is identical to v1 and matches the upstream PRD-1.1-v2 rule that no `RiskChangeProfile` is fabricated when the current scoped point cannot be populated honestly.

`ValueError` request-validation cases (`lookback_window != 60`, blank `snapshot_id`, `compare_to_date > as_of_date`) propagate from the upstream service unchanged, exactly as in v1.

### Import rules

Unchanged from v1 with one addition (telemetry):

- `from src.modules.risk_analytics import RiskChangeProfile, get_risk_change_profile`
- `from src.modules.risk_analytics.contracts import MeasureType, NodeRef, SummaryStatus, VolatilityChangeFlag, VolatilityRegime`
- `from src.modules.risk_analytics.fixtures import FixtureIndex`
- `from src.shared import ServiceError`
- `from src.shared.telemetry import emit_operation, node_ref_log_dict, timer_start`
- `from datetime import date`

The walker still must not import:

- `src.modules.risk_analytics.service` directly
- any private helper, internal constant, or non-`__all__` symbol from `src.modules.risk_analytics` or its submodules
- any classifier internal to volatility logic (e.g., `_classify_volatility_regime`, `_classify_volatility_change_flag`)
- anything from `agent_runtime`

## Classification vocabularies and inference rules

All vocabularies are closed enums (`StrEnum`) per ADR-001. Any addition to a vocabulary requires a `walker_version` bump and a PRD update.

All inference rules below are deterministic and use only fields already present on the upstream `RiskChangeProfile` (and the `SummaryStatus`, `VolatilityRegime`, `VolatilityChangeFlag` enums it carries). No new thresholds are computed against external state. No wall-clock. The walker uses the typed enum values directly (no parsing, no string comparison beyond enum equality).

Throughout this section, `profile` refers to the `RiskChangeProfile` returned by the upstream service. All field references (`profile.delta_abs`, `profile.rolling_std`, etc.) are field accesses on that typed object. Per PRD-1.1-v2 "Delta field semantics (normative)", `profile.delta_abs` and `profile.delta_pct` are `None` when `previous_value` is `None`, and `profile.delta_pct` is `None` when `previous_value == 0`. Per PRD-1.1-v2 "Minimum-history rules", `profile.rolling_std` is `None` when fewer than 2 valid points are available in the lookback window. Inference rules below handle each null path explicitly.

### `ChangeKind` vocabulary

```text
FIRST_ORDER_DRIVEN
SECOND_ORDER_DRIVEN
COMBINED
NEUTRAL
INDETERMINATE
```

### `ChangeKind` inference rule (deterministic; precedence top-to-bottom; first match wins)

Inputs (all from `profile`): `delta_abs`, `delta_pct`, `rolling_std`, `volatility_regime`, `volatility_change_flag`, `status`.

Helper definitions (used by both this rule and the significance rule):

- **`first_order_material`** is `True` when at least one of:
  - `profile.rolling_std is not None and profile.rolling_std > 0 and profile.delta_abs is not None and abs(profile.delta_abs) >= 1.0 * profile.rolling_std`
  - `profile.delta_pct is not None and abs(profile.delta_pct) >= 0.05`

  Otherwise `False`. The `1.0 * rolling_std` 1-sigma comparison is the primary materiality signal; the `5%` percentage-delta fallback applies when `rolling_std` is absent or zero but `delta_pct` is available.

- **`second_order_active`** is `True` when at least one of:
  - `profile.volatility_regime in {VolatilityRegime.ELEVATED, VolatilityRegime.HIGH}`
  - `profile.volatility_change_flag == VolatilityChangeFlag.RISING`

  Otherwise `False`.

- **`volatility_indeterminate`** is `True` when both:
  - `profile.volatility_regime == VolatilityRegime.INSUFFICIENT_HISTORY`
  - `profile.volatility_change_flag == VolatilityChangeFlag.INSUFFICIENT_HISTORY`

  Otherwise `False`.

Rule (precedence top-to-bottom; first match wins):

1. if `profile.delta_abs is None and volatility_indeterminate` → `INDETERMINATE`
2. else if `first_order_material and second_order_active` → `COMBINED`
3. else if `first_order_material` → `FIRST_ORDER_DRIVEN`
4. else if `second_order_active` → `SECOND_ORDER_DRIVEN`
5. else → `NEUTRAL`

`INDETERMINATE` reflects the case where neither first-order nor second-order signal is available (no comparison value AND no volatility classification). When delta is absent (`MISSING_COMPARE`) but volatility classification is available, the rule resolves to `SECOND_ORDER_DRIVEN` (rule 4) or `NEUTRAL` (rule 5) — `delta_abs is None` does not by itself force `INDETERMINATE`, since the volatility context may still be meaningful.

### `SignificanceLevel` vocabulary

```text
LOW
MODERATE
HIGH
INSUFFICIENT_DATA
```

### `SignificanceLevel` inference rule (deterministic; precedence top-to-bottom; first match wins)

Inputs (all from `profile`): `delta_abs`, `delta_pct`, `rolling_std`, `volatility_regime`.

Reuse the `first_order_material` helper from `ChangeKind`.

Helper definition for this rule:

- **`first_order_high`** is `True` when at least one of:
  - `profile.rolling_std is not None and profile.rolling_std > 0 and profile.delta_abs is not None and abs(profile.delta_abs) >= 2.0 * profile.rolling_std`
  - `profile.delta_pct is not None and abs(profile.delta_pct) >= 0.20`

  Otherwise `False`. The `2.0 * rolling_std` 2-sigma comparison is the primary high-significance signal; the `20%` percentage-delta fallback applies when `rolling_std` is absent or zero.

Rule (precedence top-to-bottom; first match wins):

1. if `profile.delta_abs is None and (profile.rolling_std is None or profile.rolling_std == 0) and profile.delta_pct is None` → `INSUFFICIENT_DATA`
2. else if `first_order_high` → `HIGH`
3. else if `first_order_high is False and profile.volatility_regime == VolatilityRegime.HIGH and first_order_material` → `HIGH`
4. else if `first_order_material` → `MODERATE`
5. else → `LOW`

Rationale (informational, not normative): rule 3 promotes a moderate first-order move to `HIGH` when the volatility regime is itself `HIGH` — this captures the Quant Walker charter principle that "a small delta does not imply low risk if rolling volatility is elevated" (PRD-1.1-v2 business rule 10). Rule 1 reaches `INSUFFICIENT_DATA` only when both delta and dispersion are unobservable, which corresponds to `MISSING_COMPARE` combined with insufficient history; in that case the walker has nothing on which to anchor a magnitude assessment.

### `ConfidenceLevel` vocabulary

```text
HIGH
MEDIUM
LOW
```

`ConfidenceLevel` is a three-level enum because the upstream service's reachable in-object statuses for `get_risk_change_profile` are `OK`, `DEGRADED`, `MISSING_COMPARE`, and `MISSING_HISTORY` (per PRD-1.1-v2 §"Status model"). A four-level enum would create unused states. `ServiceError` outcomes (`UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`) propagate as errors and never produce a `QuantInterpretation`, so confidence does not need a "no answer" level.

### `ConfidenceLevel` inference rule (deterministic; precedence top-to-bottom; first match wins)

Inputs (all from `profile`): `status`, `volatility_regime`, `volatility_change_flag`.

Note on data-quality input scope: the task brief mentions "trust state, `assessment_status`, snapshot completeness" as confidence inputs. `trust_state` and `assessment_status` are owned by the Data Controller Walker / `controls_integrity` service (per PRD-2.1 / PRD-4.1); the Quant Walker has no access to them and must not invent them. Cross-walker integration is the orchestrator's responsibility (PRD-5.1-v2). The Quant Walker's confidence is derived solely from `RiskChangeProfile.status` (which carries snapshot completeness information via `DEGRADED`, `MISSING_COMPARE`, `MISSING_HISTORY`) and the volatility-classification fields. The orchestrator may downgrade or augment a per-target confidence view by combining Quant `confidence` with Data Controller `trust_state` when synthesizing per-target output (PRD-5.1-v2 concern).

Rule (precedence top-to-bottom; first match wins):

1. if `profile.status == SummaryStatus.OK and profile.volatility_regime != VolatilityRegime.INSUFFICIENT_HISTORY and profile.volatility_change_flag != VolatilityChangeFlag.INSUFFICIENT_HISTORY` → `HIGH`
2. else if `profile.status in {SummaryStatus.MISSING_COMPARE, SummaryStatus.MISSING_HISTORY}` → `LOW`
3. else if `profile.status == SummaryStatus.DEGRADED` → `MEDIUM`
4. else if `profile.volatility_regime == VolatilityRegime.INSUFFICIENT_HISTORY or profile.volatility_change_flag == VolatilityChangeFlag.INSUFFICIENT_HISTORY` → `MEDIUM`
5. else → `MEDIUM` (defensive default; not reachable in v1 given PRD-1.1-v2 reachable in-object statuses, but kept to make the function total)

### `QuantCaveatCode` vocabulary

Closed v2 vocabulary:

```text
COMPARE_POINT_MISSING
HISTORY_INSUFFICIENT
PROFILE_DEGRADED
VOLATILITY_REGIME_INDETERMINATE
VOLATILITY_CHANGE_FLAG_INDETERMINATE
```

Any addition to this vocabulary requires a `walker_version` bump and a PRD update. PRD-2.1 `ReasonCode` and PRD-1.1-v2 status strings are not reused as caveat codes; this is a walker-specific typed vocabulary scoped to interpretive caveats only. `caveats` is structured (typed enum tuple), not narrative prose.

### `QuantCaveatCode` inference rule (deterministic; emit one of each applicable code; deduplicate; lexicographic ascending order)

Each code is emitted iff its trigger condition holds. Order in the returned tuple is lexicographic ascending. No code is emitted more than once.

| Caveat code | Trigger condition |
| --- | --- |
| `COMPARE_POINT_MISSING` | `profile.status == SummaryStatus.MISSING_COMPARE` |
| `HISTORY_INSUFFICIENT` | `profile.status == SummaryStatus.MISSING_HISTORY` |
| `PROFILE_DEGRADED` | `profile.status == SummaryStatus.DEGRADED` |
| `VOLATILITY_REGIME_INDETERMINATE` | `profile.volatility_regime == VolatilityRegime.INSUFFICIENT_HISTORY` |
| `VOLATILITY_CHANGE_FLAG_INDETERMINATE` | `profile.volatility_change_flag == VolatilityChangeFlag.INSUFFICIENT_HISTORY` |

If `profile.status == SummaryStatus.OK`, no status-derived caveat codes are emitted; volatility-derived caveats remain independent.

### `InvestigationHint` vocabulary

Closed v2 vocabulary:

```text
INVESTIGATE_VOLATILITY_REGIME
INVESTIGATE_VOLATILITY_CHANGE
INVESTIGATE_DATA_COMPLETENESS
INVESTIGATE_COMPARE_GAP
INVESTIGATE_LARGE_FIRST_ORDER
```

`InvestigationHint` is a typed pointer set, not a directive. It indicates which dimension(s) of the underlying data deserve a deeper look. The orchestrator (PRD-5.1-v2) may use these hints to inform routing decisions, but no routing is dictated by this PRD. The Quant Walker does not invoke any other walker; cross-walker routing is owned by the orchestrator.

### `InvestigationHint` inference rule (deterministic; emit one of each applicable hint; deduplicate; lexicographic ascending order)

| Hint | Trigger condition |
| --- | --- |
| `INVESTIGATE_VOLATILITY_REGIME` | `profile.volatility_regime in {VolatilityRegime.ELEVATED, VolatilityRegime.HIGH}` |
| `INVESTIGATE_VOLATILITY_CHANGE` | `profile.volatility_change_flag == VolatilityChangeFlag.RISING` |
| `INVESTIGATE_DATA_COMPLETENESS` | `profile.status in {SummaryStatus.DEGRADED, SummaryStatus.MISSING_HISTORY}` |
| `INVESTIGATE_COMPARE_GAP` | `profile.status == SummaryStatus.MISSING_COMPARE` |
| `INVESTIGATE_LARGE_FIRST_ORDER` | `significance == SignificanceLevel.HIGH` (computed by this walker per the rule above) |

Note: `INVESTIGATE_LARGE_FIRST_ORDER` is the only hint computed against a walker-derived field; all others are derived directly from upstream typed fields. Since `significance` is itself deterministic over upstream fields, the full `investigation_hints` tuple remains deterministic.

## Hierarchy localization decision

**Decision:** Hierarchy localization is **explicitly deferred to v3** (Quant Walker v3 — Hierarchy-Aware Output, future PRD).

**Rationale:**

1. The upstream `risk_analytics` service has no public API today for traversing or comparing across child nodes of a `node_ref`. `get_risk_change_profile` is single-node-scoped per PRD-1.1-v2.
2. Multi-node walker invocation (the alternative implementation) is structurally an orchestrator concern: invoking the walker N times across a node hierarchy is a workflow pattern, not a walker-internal capability. PRD-5.1-v2 (multi-walker orchestration) has not yet specified hierarchy fan-out routing; introducing it inside the walker would pre-commit a contract decision that belongs to the orchestrator.
3. A "structured placeholder" (e.g., a typed `localization: Localization | None` field set to `None` in v2) would create a contract surface with no implementation and no test coverage, which violates the typed-schema discipline in ADR-001. Better to add the field together with the implementation when v3 lands.
4. The current `node_ref` identifies the scope; downstream consumers can recover hierarchy context from `node_ref.node_level`, `node_ref.hierarchy_scope`, and `node_ref.legal_entity_id` directly if they need it. No interpretive value is lost in v2 by deferring localization.

**v3 trigger:** PRD-4.2-v3 should be authored when at least one of the following is true: (a) PRD-5.1-v2 specifies a hierarchy fan-out routing pattern that requires a per-target localization output; (b) `risk_analytics` adds a public API to retrieve or compare child-node `RiskChangeProfile` values for a parent `node_ref`; (c) Governance / Reporting Walker v1 documents a concrete need for hierarchy-localized inputs. None of these conditions hold today.

## Multi-function delegation decision

**Decision:** v2 exposes **exactly one** entry point — `summarize_change` over `get_risk_change_profile` — as in v1. v2 does **not** add `summarize_summary`, `summarize_delta`, or `summarize_history` walker entry points.

**Rationale:**

1. PRD-5.1-v2 (the only currently planned downstream consumer that drives multi-function need) has not been authored yet. This PRD's downstream consumer contract specifies what PRD-5.1-v2 will consume from the walker, and that contract is fully expressed via `summarize_change`. PRD-5.1-v2 routing per target invokes the walker exactly once per target with the same `(node_ref, measure_type, as_of_date, snapshot_id)` it already passes to `data_controller.assess_integrity` — no first-order-only fast path or history-only path is required for multi-walker orchestration.
2. `RiskChangeProfile` carries strict supersets of the fields in `RiskDelta` (no `volatility_*` or rolling fields) and `RiskSummary` (no `volatility_*` fields). Any orchestrator or downstream walker that needs first-order-only or summary-only data can read those fields off `QuantInterpretation.risk_change_profile` directly. Adding parallel walker entry points purely to expose subsets would create three more typed contract surfaces with no concrete consumer requirement.
3. The Time Series Walker v1 PRD (per `docs/roadmap/module_1_var_dashboard.md`, in flight as a sibling MVP item) is the natural home for history-series interpretation, not a Quant Walker `summarize_history` delegate. Pre-exposing `summarize_history` would risk overlap with the Time Series Walker's remit.
4. Adding entry points later is purely additive (new functions in `src/walkers/quant/__init__.py`). Deferring is the safe, narrowest direction consistent with the repository's "narrowest reviewable slice" preference.

**v3 trigger:** A future PRD-4.2-v3 may add additional walker entry points when, and only when, at least one downstream consumer PRD documents a concrete contract requirement for them (e.g., PRD-5.1-v3 routing that needs a fast first-order-only delegate for budget reasons; or a Governance / Reporting Walker v2 PRD that needs a history-series delegate for a non-Time-Series use case). Until that concrete requirement exists, this decision stands.

## Downstream consumer contract

This section is the binding contract that PRD-5.1-v2 (multi-walker orchestration) will reference verbatim when specifying Quant Walker routing and per-target synthesis.

### Walker entry point exposed to PRD-5.1-v2

```python
from src.walkers.quant import summarize_change

result: QuantInterpretation | ServiceError = summarize_change(
    node_ref=...,           # NodeRef
    measure_type=...,       # MeasureType
    as_of_date=...,         # date
    snapshot_id=...,        # str (orchestrator pins; not None per PRD-5.1 §"Replay and determinism")
    fixture_index=...,      # FixtureIndex (orchestrator's risk fixture index)
)
```

The orchestrator must pass `snapshot_id` explicitly (it is non-`None` in any PRD-5.1 v1+ context per the orchestrator's replay invariant). The orchestrator must use the default `lookback_window=60` and `require_complete=False` unless and until a future PRD documents an alternative requirement; v2 does not introduce orchestrator-side overrides. `compare_to_date` defaults to the upstream service's prior-business-day default and is not reset by the orchestrator in MVP scope.

### Output type the orchestrator can expect

`QuantInterpretation | ServiceError` (typed union). The orchestrator must:

- **propagate `QuantInterpretation` by reference** into its per-target result; it must not mutate, transform, recompute, or reshape any field, including the nested `risk_change_profile` and the typed enum fields. This rule mirrors the rule already in PRD-5.1 v1 for `IntegrityAssessment`.
- **propagate `ServiceError` by reference** into its per-target result; it must not catch, re-wrap, or substitute the error.
- **introduce no orchestrator-side inference rules** over `change_kind`, `significance`, `confidence`, `caveats`, or `investigation_hints`. These are walker-emitted classifications; the orchestrator may read them for routing decisions but must not redefine them.

### Per-target synthesis pattern (binding for PRD-5.1-v2)

PRD-5.1-v2 should extend the existing `TargetInvestigationResult` pattern (defined in PRD-5.1 v1) with an additional optional nested field that holds the Quant Walker output for the same target. The exact field name and the synthesis pattern are owned by PRD-5.1-v2; this PRD provides the typed shape it must accept:

- `quant_interpretation: QuantInterpretation | None` — present iff the orchestrator routed to the Quant Walker for this target and the walker returned a `QuantInterpretation`
- `quant_service_error: ServiceError | None` — present iff the orchestrator routed to the Quant Walker for this target and the walker returned a `ServiceError`

The orchestrator's challenge gate (PRD-5.1-v2 may extend the v1 challenge gate) may consult `QuantInterpretation.confidence` and `QuantInterpretation.significance` as inputs to `handoff_status` assignment, but the orchestrator must not redefine these vocabularies, must not introduce orchestrator-originated quant codes, and must not override the existing `IntegrityAssessment.trust_state` precedence (which currently dominates `handoff_status` per PRD-5.1 v1 §"Per-target gate rules"). Specifically:

- a `BLOCKED` `trust_state` from the Data Controller Walker still results in `HOLD_BLOCKING_TRUST` regardless of Quant Walker output
- the orchestrator may add Quant-derived `handoff_status` values in PRD-5.1-v2 (e.g., a `PROCEED_WITH_QUANT_CAVEAT` status), but those are orchestrator-side decisions, not walker-side outputs

### Replay invariants the orchestrator can rely on

- Equal `(node_ref, measure_type, as_of_date, snapshot_id, fixture_index_state)` inputs produce equal `QuantInterpretation` values, field-for-field, including the nested `risk_change_profile`. This holds because (a) the upstream service is replay-deterministic per PRD-1.1-v2 and (b) all walker inference rules are deterministic over upstream typed fields.
- `QuantInterpretation` carries no wall-clock value of its own (`generated_at` lives on `risk_change_profile`).
- `walker_version` is pinned at module level and bumped only by an explicit work item; any change to the typed contracts, vocabularies, or inference rules in this PRD requires a `walker_version` bump.

### Forbidden orchestrator behaviors (binding)

- recomputing `change_kind`, `significance`, or `confidence` from upstream fields the orchestrator can also see
- emitting orchestrator-originated quant caveat codes
- collapsing or deduplicating walker `caveats` or `investigation_hints` across targets
- substituting any field on `QuantInterpretation` with an orchestrator-derived value
- generating narrative or recommended-next-step prose from `QuantInterpretation` fields (those remain typed pointers; narrative is post-MVP and lives in the future Governance / Reporting Walker)

## Telemetry requirements

### Adoption status change

The shared-infra adoption matrix row for `src/walkers/` currently reads (`docs/shared_infra/adoption_matrix.md`):

```text
| `src/walkers/` | telemetry contract | adopted | `data_controller` walker emits via `src.shared.telemetry.emit_operation` (WI-4.1.4) |
```

The Quant Walker v2 implementation must extend this coverage to the Quant Walker. The adoption-matrix `Notes` column must be updated to reflect Quant Walker telemetry coverage (e.g., extend the existing note: "`data_controller` and `quant` walkers emit via `src.shared.telemetry.emit_operation` (WI-4.1.4, WI-<assigned>)"). The status remains `adopted`. This change rolls into the telemetry-adoption WI; see "Issue decomposition guidance".

### Required event

The walker must emit exactly one structured operation event per `summarize_change` invocation, regardless of whether the upstream returned a `RiskChangeProfile` or a `ServiceError`. The event is emitted at function exit, mirroring the pattern in `src/walkers/data_controller/walker.py`.

### Event shape (minimum payload, normative)

Implemented via `src.shared.telemetry.emit_operation`. The walker must use the shared helper directly; no module-local status mapping or duplicate framework. Call shape matches `emit_operation(operation, *, status=..., start_time=..., include_trace_context=..., **context)` in `src/shared/telemetry/operation_log.py`:

- `operation`: positional first argument; value `"summarize_change"`
- `status`: keyword-only; see "Status mapping" below
- `start_time`: keyword-only; monotonic anchor captured before the upstream call via `timer_start()`
- `include_trace_context`: keyword-only; `False` (consistent with `risk_analytics` and `data_controller` walker; OpenTelemetry trace keys are not adopted as a parallel evidence surface in v2)
- `node_ref`: `node_ref_log_dict(node_ref)` (canonical low-cardinality dict)
- `measure_type`: the input `MeasureType` value (the shared helper handles enum serialization)
- `as_of_date`: the input `date`
- `snapshot_id`: the input `snapshot_id` (may be `None`)

When the outcome is a `QuantInterpretation`, the walker must additionally attach low-cardinality typed enum fields to the payload (these are stable, low-cardinality, and useful for triage):

- `change_kind`: the resolved `ChangeKind` value
- `significance`: the resolved `SignificanceLevel` value
- `confidence`: the resolved `ConfidenceLevel` value

When the outcome is a `ServiceError`, the three fields above must be explicitly `None` (per the shared telemetry payload-discipline rule that conditional fields must be present in the payload with explicit `None` rather than absent keys, per `docs/shared_infra/telemetry.md`).

### Status mapping

The `status` argument value:

- when the outcome is a `ServiceError`: the `ServiceError.status_code` (a string like `"MISSING_NODE"`) — identical to the data_controller walker's pattern
- when the outcome is a `QuantInterpretation`: the upstream `risk_change_profile.status.value` (e.g., `"OK"`, `"DEGRADED"`, `"MISSING_COMPARE"`, `"MISSING_HISTORY"`)

The shared telemetry helper owns the status-to-log-level mapping (`_INFO_STATUSES`, `_WARNING_STATUSES` in `src/shared/telemetry/operation_log.py`); the walker must not reimplement it.

### Forbidden telemetry behaviors

- importing `agent_runtime` for any reason
- emitting raw fixture data, full `RiskChangeProfile` payloads, or large arrays in the event payload (per shared payload discipline)
- emitting more than one event per `summarize_change` invocation
- duplicating status-to-level mapping inside the walker package
- emitting walker-side narrative or free-text fields

## Replay and evidence

The walker preserves all v1 replay and evidence guarantees. New v2 considerations:

- All interpretive fields are deterministic over the upstream `RiskChangeProfile` typed fields. Same inputs → same `RiskChangeProfile` (per PRD-1.1-v2 replay invariant) → same `QuantInterpretation`.
- `QuantInterpretation.walker_version` provides the version anchor for replay determinism of the walker layer itself (analogous to `service_version` for `risk_analytics` and `orchestrator_version` for the orchestrator).
- No new `data_version`, `snapshot_id`, `service_version`, `generated_at`, or `evidence_refs` field is introduced at the `QuantInterpretation` level. Those fields remain on the nested `RiskChangeProfile` per ADR-002 / ADR-003 (no parallel evidence surface).
- The walker introduces no module-local `current_trace_context()` calls beyond what `emit_operation` does internally. Trace context is not part of the typed contract.

## Acceptance criteria

### Functional

- `summarize_change` is importable as `from src.walkers.quant import summarize_change`
- For any valid input where `get_risk_change_profile` returns a `RiskChangeProfile`, `summarize_change` returns a `QuantInterpretation` whose `risk_change_profile` field is structurally equal to the upstream return value (`==` on the frozen Pydantic model)
- For any input where `get_risk_change_profile` returns a `ServiceError`, `summarize_change` returns the same `ServiceError` instance unchanged (identity-equal where the upstream returns a singleton; field-equal in all cases)
- For each documented `ValueError` case, `summarize_change` raises the same `ValueError` (same message) the upstream service raises
- `change_kind`, `significance`, `confidence`, `caveats`, `investigation_hints` are computed exactly per the inference rules in this PRD, for every reachable combination of upstream typed input fields covered by the existing `risk_analytics` fixtures

### Contract

- `QuantInterpretation` is a frozen Pydantic model with `extra="forbid"` and field types per "Output type — `QuantInterpretation`"; `ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode`, `InvestigationHint` are `StrEnum` per ADR-001
- `summarize_change` return type annotation is exactly `QuantInterpretation | ServiceError` — no broader union, no `Optional`, no `Any`
- `walker_version` is pinned at module level (`QUANT_WALKER_VERSION` constant) in `src/walkers/quant/walker.py` and is non-empty
- No imports of private service internals (only public `risk_analytics` API plus the established `contracts` / `fixtures` submodule type imports plus shared telemetry)
- No new walker-public types beyond `QuantInterpretation` and the five enums; no parallel error envelope; no new status vocabulary
- `QuantInterpretation` does not duplicate `snapshot_id`, `data_version`, `service_version`, or `generated_at` at the top level

### Architecture

- Quant logic remains in `src/modules/risk_analytics/`; the walker is interpretive-only over typed upstream output
- Walker package location remains `src/walkers/quant/` per `src/walkers/README.md`
- New file src/walkers/quant/contracts.py (or equivalent module per repo convention) hosts `QuantInterpretation` and the five enums; the existing `src/walkers/quant/walker.py` is updated in-place to import them and emit telemetry (contracts path is planned by WI-4.2.4, not yet on `main`)
- No coupling to PRD-5.1 orchestrator code; no coupling to any other walker; no coupling to `agent_runtime`

### Test

- Unit tests cover every documented inference-rule branch for `change_kind`, `significance`, `confidence`, `caveats`, and `investigation_hints` against the existing `risk_analytics` fixture surface
- Tests cover at minimum: every reachable in-object `SummaryStatus` for `get_risk_change_profile` (`OK`, `DEGRADED`, `MISSING_COMPARE`, `MISSING_HISTORY`); both `INSUFFICIENT_HISTORY` enum values for volatility fields; `previous_value is None` and `previous_value == 0` paths; representative `ServiceError` propagation cases (`UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, `MISSING_NODE`)
- Replay-equality test: invoking `summarize_change` twice with identical inputs produces field-for-field equal `QuantInterpretation` objects (and identical `walker_version`)
- Telemetry test: one `summarize_change` invocation emits exactly one `operation` event via `src.shared.telemetry`, the payload contains the documented minimum fields, and `change_kind` / `significance` / `confidence` are explicit `None` on `ServiceError` paths
- Existing v1 parity tests (PRD-4.2 v1 §"Test intent") must be updated to assert that `summarize_change(...).risk_change_profile == get_risk_change_profile(...)` rather than `summarize_change(...) == get_risk_change_profile(...)`. This is the only contract migration required for downstream tests; downstream consumers other than these tests do not exist on `main`.
- If existing fixtures do not cover a documented inference branch, the coding agent should cover the maximal subset reachable with current fixtures and explicitly note any gap as a follow-up WI; do not invent new fixture infrastructure inside the walker package (per v1 discipline)

## Test intent

Tests must prove three things:

1. **Faithful propagation:** the upstream `RiskChangeProfile` is preserved verbatim inside `QuantInterpretation.risk_change_profile`, and `ServiceError` paths propagate unchanged
2. **Deterministic interpretation:** every inference rule in this PRD produces the documented enum value for every reachable combination of upstream typed input fields
3. **Replay safety:** equal inputs produce equal outputs, and the walker introduces no wall-clock dependency

**Pattern for inference-rule tests:** for each rule branch, construct (or load from fixtures) a `RiskChangeProfile` whose typed fields trigger that branch, invoke `summarize_change`, and assert the returned `QuantInterpretation` field equals the documented expected enum value. Use parametrized table-driven tests; prefer explicit per-rule rows over broad "smoke" tests so reviewers can trace each row back to a rule clause in this PRD.

**Pattern for replay tests:** invoke `summarize_change` twice with identical arguments under a fixed fixture-index state; assert the two returned `QuantInterpretation` objects are field-for-field equal (Pydantic equality on frozen models is value-equality).

**Pattern for telemetry tests:** install a stdlib `logging` handler on `src.shared.telemetry.LOGGER_NAME`, invoke `summarize_change`, assert exactly one `EVENT_NAME` (`"operation"`) record, inspect the structured payload for the documented minimum fields and value types.

## Issue decomposition guidance

This PRD decomposes into a small ordered slice sequence. Each slice is a bounded, reviewable WI. The Issue Planner derives concrete WI files; the names below are guidance, not normative WI IDs.

1. **WI-4.2.3 — Quant Walker v2 implementation PRD** (this document; mirrors the WI-4.1.1 / WI-4.2.1 PRD-merge slice). Merges this PRD to `main` so downstream WIs can cite a stable contract.

2. **WI-4.2.4 — Quant Walker v2 typed contracts.** Add src/walkers/quant/contracts.py (or equivalent module) defining `QuantInterpretation`, `ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode`, `InvestigationHint`, and the `QUANT_WALKER_VERSION` constant. Add typed-contract construction tests (frozen, `extra="forbid"`, enum membership). No behavior change to `summarize_change` in this slice; the walker still imports the new types but `summarize_change` continues to return `RiskChangeProfile | ServiceError` until WI-4.2.5. (This separation lets the typed contract review happen before the inference-rule review.) Planned path only until WI-4.2.4 merges.

3. **WI-4.2.5 — Quant Walker v2 interpretive logic.** Update `src/walkers/quant/walker.py` to compute `QuantInterpretation` per the inference rules in this PRD; widen the return type annotation; update existing v1 parity tests to dereference `.risk_change_profile`. Add the full inference-rule test matrix per "Test intent". Telemetry is added in the next slice to keep this slice reviewable.

4. **WI-4.2.6 — Quant Walker v2 telemetry adoption.** Add the `emit_operation` call to `summarize_change` per "Telemetry requirements". Add telemetry tests. Update `docs/shared_infra/adoption_matrix.md` to reflect Quant Walker coverage in the `src/walkers/` row notes.

5. **WI-4.2.7 — Quant Walker v2 replay-determinism tests.** Add a focused replay-equality test suite that asserts `summarize_change` is replay-stable across identical inputs and identical fixture-index state, including under each reachable upstream `SummaryStatus` and both `INSUFFICIENT_HISTORY` paths. (May be merged into WI-4.2.5 by the Issue Planner if scope permits; kept separate here for review focus.)

Sequencing: WI-4.2.3 → WI-4.2.4 → WI-4.2.5 → WI-4.2.6 → WI-4.2.7. WI-4.2.5 is the gating slice for PRD-5.1-v2 implementation work; PRD-5.1-v2 author may begin drafting in parallel using this PRD's "Downstream consumer contract" section.

No Time Series Walker WI is implied by this PRD. Time Series Walker v1 PRD is a sibling MVP item authored independently and may run in parallel.

No Governance / Reporting Walker WI is implied by this PRD. That PRD is post-MVP near-term per DECISION-MVP-02 and authored after Quant v2 and Time Series v1 are in draft.

## Open questions (genuinely deferred)

The following are explicitly deferred to v3+ with stated triggers. They are **not** items that must be decided in this PRD; each has a closed v2 decision recorded above (defer with rationale and trigger).

- **Hierarchy localization (v3):** see "Hierarchy localization decision". v3 trigger: PRD-5.1-v2 hierarchy fan-out, OR a `risk_analytics` API for child-node retrieval, OR a documented Governance / Reporting Walker need.
- **Multi-function delegation (v3):** see "Multi-function delegation decision". v3 trigger: a downstream consumer PRD documents a concrete contract requirement for `summarize_summary`, `summarize_delta`, or `summarize_history`.
- **Multi-target / batch invocation (orchestrator concern, not walker):** Single-target single-measure remains the walker contract. Batch and fan-out are PRD-5.1-v2+ orchestrator concerns and are outside the Quant Walker remit per `docs/05_walker_charters.md` (walkers answer bounded questions; orchestrators own routing).
- **Quant Walker exemplar alignment (no exemplar exists):** No docs/prd_exemplars/PRD-4.2-quant-walker.md exists. If one is authored, this PRD should be reviewed for alignment before any v3+ behavior is added. Non-blocking for v2.
- **Extending `QuantCaveatCode` and `InvestigationHint` vocabularies:** the v2 vocabularies are closed. Any addition (e.g., a future `STALE_DATA_SUSPECTED` caveat from a Time Series Walker integration) requires a `walker_version` bump and a PRD update; cross-walker integration is the orchestrator's concern.
- **Confidence input expansion (cross-walker):** the task brief mentions `trust_state` and `assessment_status` as confidence inputs; those live on `IntegrityAssessment` and are outside the Quant Walker's remit. If a future Module 1 capability requires a unified per-target confidence (combining Quant `confidence`, Data Controller `trust_state`, and Time Series confidence), that synthesis is an orchestrator-side concern (PRD-5.1-v2 or v3) and must not be embedded inside the Quant Walker.

The following are **not** open questions because they are explicitly closed in this PRD:

- output type shape (closed: `QuantInterpretation | ServiceError` with the field list above)
- first-order vs second-order distinction (closed: `ChangeKind` enum + deterministic rule)
- significance / materiality (closed: `SignificanceLevel` enum + deterministic rule)
- confidence model (closed: `ConfidenceLevel` enum + deterministic rule)
- candidate areas for deeper investigation (closed: `InvestigationHint` typed tuple + deterministic rule)
- telemetry adoption (closed: `emit_operation` per `data_controller` pattern; adoption-matrix update in WI-4.2.6)
- downstream consumer contract for PRD-5.1-v2 (closed: see "Downstream consumer contract")

## Reviewer checklist

- Walker v2 introduces interpretive output but does **not** introduce any new quantitative semantics. Every inference rule reads only typed fields already on `RiskChangeProfile` (`delta_abs`, `delta_pct`, `rolling_std`, `volatility_regime`, `volatility_change_flag`, `status`).
- PRD-1.1-v2 service semantics are unchanged. Status precedence, delta-field rules, volatility-rules-v1, replay/version metadata are cross-referenced, not restated or altered.
- `QuantInterpretation` is frozen, `extra="forbid"`, and propagates the upstream `RiskChangeProfile` by reference. No field on `RiskChangeProfile` is mutated, recomputed, or shadowed by a duplicate top-level field on `QuantInterpretation`.
- All five new vocabularies (`ChangeKind`, `SignificanceLevel`, `ConfidenceLevel`, `QuantCaveatCode`, `InvestigationHint`) are closed `StrEnum` per ADR-001.
- All inference rules are deterministic, total (cover the full reachable input space), and use precedence-based "first match wins" semantics.
- The `change_kind` rule and the `significance` rule share the `first_order_material` helper definition exactly; no duplicated threshold constants.
- `confidence` is derived solely from upstream typed fields the Quant Walker can see; it does not invent `trust_state` or `assessment_status` access (those live on `IntegrityAssessment` and belong to the Data Controller Walker).
- The walker emits exactly one `emit_operation` event per invocation, with `include_trace_context=False`, the documented minimum payload, and explicit `None` on conditional fields when the outcome is a `ServiceError`.
- The `src/walkers/` adoption-matrix row in `docs/shared_infra/adoption_matrix.md` is updated to reflect Quant Walker coverage (notes column extension; status remains `adopted`).
- `walker_version` is pinned at module level (`QUANT_WALKER_VERSION`) and bumped only for contract / vocabulary / inference-rule changes; the PR includes a note on the version chosen.
- No new ADR-level concept; no new shared-infra contract; no schema change to PRD-1.1-v2 contracts has leaked in.
- The downstream consumer contract section is sufficient for the PRD-5.1-v2 author to specify Quant Walker routing without further negotiation with this PRD's author.
- Hierarchy localization, multi-function delegation, batch invocation, and narrative output remain explicitly out of scope; the deferral rationale and v3 trigger are recorded.
- Single entry point preserved: `summarize_change` over `get_risk_change_profile` — no `summarize_summary` / `summarize_delta` / `summarize_history` added in v2.
- Backtick-wrapped repository paths in this PRD all exist on `main` as of WI-4.2.2 merge (PR #168) — `src/walkers/quant/`, `src/walkers/quant/walker.py`, `src/walkers/quant/__init__.py`, `src/walkers/data_controller/`, `src/walkers/README.md`, `src/modules/risk_analytics/`, `src/modules/risk_analytics/contracts/`, `src/modules/risk_analytics/fixtures/`, `src/shared/`, `src/shared/telemetry/`, all `docs/...` paths — consistent with reference-integrity and registry-alignment checks. The planned src/walkers/quant/contracts.py module (WI-4.2.4) is named in prose only where it does not yet exist on `main` (no backticks), matching PRD-4.2 v1 planned-component discipline.

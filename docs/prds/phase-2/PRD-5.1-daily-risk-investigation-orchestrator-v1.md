# PRD-5.1: Daily Risk Investigation Orchestrator v1

## Header

- **PRD ID:** PRD-5.1
- **Title:** Daily Risk Investigation Orchestrator v1 — Bounded Workflow Slice
- **Phase:** Phase 2
- **Status:** Ready for implementation
- **Layer:** Orchestrator
- **Type:** Bounded workflow runner (single walker, single trigger, return-by-value state)
- **Primary owner:** Technical Owner, Daily Risk Investigation
- **Process owner:** Market Risk Process Owner
- **Control owner:** Risk Data / Production Controls Owner
- **Upstream service PRDs:** PRD-1.1-v2 (Risk Summary Service), PRD-2.1 (Controls and Production Integrity Assessment Service)
- **Upstream walker PRDs:** PRD-4.1 (Data Controller Walker v1)
- **Related ADRs:** ADR-001 (schema and typing), ADR-002 (replay and snapshot model), ADR-003 (evidence and trace model), ADR-004 (business-day and calendar handling)
- **Related shared infra:** `docs/shared_infra/index.md`, `docs/shared_infra/telemetry.md`, `docs/shared_infra/adoption_matrix.md`
- **Related components (planned scaffolding, created by WI-5.1.1):** `src/orchestrators/daily_risk_investigation/` <!-- drift-ignore -->
- **Existing components consumed:** `src/modules/risk_analytics/` (`get_risk_summary`), `src/modules/controls_integrity/` (`IntegrityAssessment`), `src/shared/` (`ServiceError`), `src/walkers/data_controller/` (`assess_integrity`)
- **Exemplar (non-normative background only):** `docs/prd_exemplars/PRD-5.1-daily-risk-investigation-orchestrator.md`

## Purpose

Provide the first implementation of the Daily Risk Investigation orchestrator: a bounded, replayable, single-walker workflow that drives one daily run from explicit trigger through readiness gate, target selection, walker routing, per-target synthesis, deterministic challenge gate, and structured handoff.

This v1 slice exists to make the orchestrator layer real — moving `src/orchestrators/` from a permanently `planned` placeholder in the shared-infra adoption matrix to a working, tested, telemetry-emitting workflow runner — while preserving the architectural rule that orchestrators own workflow state, routing, gates, retries, and handoff only.

The orchestrator does not own deterministic trust logic, materiality logic, market-risk calculation, narrative generation, governance approval lifecycle, or UI rendering. Those concerns remain in their respective owning layers.

## Why this is the v1 slice

The repository now has a deterministic service slice (PRD-2.1), a thin walker delegate slice (PRD-4.1), and an upstream risk-summary service (PRD-1.1-v2). PRD-2.1 and PRD-4.1 both name the Daily Risk Investigation orchestrator as their next consumer. `src/orchestrators/README.md` already lists `daily_risk_investigation/` as the first planned orchestrator root, and the shared-infra adoption matrix lists `src/orchestrators/` telemetry as `planned` with no implementation path.

Before the orchestrator layer can take on richer concerns (multi-walker routing, materiality logic, governance handoff, human-in-the-loop challenge), the workflow boundary itself must exist and be tested. v1 establishes that boundary with the minimum viable workflow that exercises every required stage exactly once with one walker.

Richer orchestrator behavior (multi-walker routing, materiality determination, signed escalation, durable persistence, monthly committee orchestration, governance pack integration) is explicitly out of scope and is a v2+ concern.

## Supported process context

This PRD supports:

- daily risk monitoring run lifecycle
- programmatic invocation of one bounded daily investigation flow over a caller-provided candidate set
- structured per-target handoff for downstream governance / reporting consumption (consumer not built in v1)

It does not provide:

- governance sign-off
- committee pack assembly
- breach approval lifecycle
- regulatory-capital interpretation

## In scope

- new `daily_risk_investigation` package under `src/orchestrators/`, created by WI-5.1.1
- single public entry point `start_daily_run` that runs one daily investigation end-to-end and returns a typed `DailyRunResult`
- one canonical run-state model (`DailyRunResult`) and supporting per-stage typed objects, all using the repo-canonical typed-schema approach (ADR-001)
- nine stages executed in fixed order: intake → readiness gate → target selection → target routing → investigation → synthesis → challenge → handoff → persist
- consumption of `RiskSummary` from `get_risk_summary` for readiness verification and target-set hydration
- consumption of `IntegrityAssessment | ServiceError` from `data_controller.assess_integrity` for per-target investigation
- deterministic per-target challenge gate driven solely by the typed fields already produced by the deterministic service (no orchestrator-owned trust rules)
- structured handoff list of `(node_ref, measure_type, handoff_status, blocking_reason_codes, cautionary_reason_codes, service_error_status_code)`, with field semantics matching the `TargetHandoffEntry` model defined below
- replay determinism: equal inputs produce equal `DailyRunResult` (ADR-002)
- evidence propagation: per-target outcomes carry the unmodified `IntegrityAssessment` (or `ServiceError`) from the walker layer (ADR-003)
- telemetry: structured operation events for the v1 stage subset enumerated in "Required events (v1)" below, plus one terminal `daily_run_complete` event, emitted via `src.shared.telemetry.emit_operation` (no module-local duplicate status mapping; no `agent_runtime` imports)
- shared-infra adoption: flip `src/orchestrators/` row in `docs/shared_infra/adoption_matrix.md` from `planned` to `adopted` once telemetry slice merges
- unit tests on contract shapes, stage ordering, gate semantics, degraded handling, and replay equality

## Out of scope

- materiality determination, scoring, ranking, or threshold logic of any kind (caller supplies the candidate `node_ref` set in v1)
- routing to any walker other than `data_controller` (no quant, time-series, controls-change, market-context, governance-reporting, critic-challenge, model-risk-usage walker integration in v1)
- human-in-the-loop challenge, signed escalation, override capture, or operator approval flow
- governance approval lifecycle, committee pack assembly, monthly orchestration, breach approval workflow
- UI rendering, analyst review console, dashboard surfaces
- durable persistence backend (in-memory return-by-value only; serialization shape is stable but no DB / filesystem writer is built)
- scheduled / cron / event-bus triggering (programmatic invocation only)
- multi-day, multi-snapshot, or batched-run orchestration
- automatic cross-run retries, retry queues, or background reconciliation
- recomputation, transformation, aggregation, or interpretation of any deterministic-service output (orchestrator must propagate typed values unchanged)
- any new canonical risk concept, trust concept, evidence shape, business-day rule, or status vocabulary
- FRTB / PLA / HPL / RTPL stages or controls
- narrative caveat generation, recommended-next-step prose, free-text findings
- redesign of PRD-1.1-v2, PRD-2.1, or PRD-4.1 contracts or status semantics
- introducing a new typed service-error envelope; orchestrator reuses `src.shared.ServiceError` and the per-target `IntegrityAssessment | ServiceError` union unchanged

## Users and consumers

Primary caller of `start_daily_run` in v1:

- programmatic test harness or operator-driven script supplying `(as_of_date, snapshot_id, candidate_targets, measure_type)`

Primary consumer of the returned `DailyRunResult`:

- downstream governance / reporting walker (future, not built in v1)
- replay harness (verifies determinism)

Human users influenced by orchestrator output (indirectly, via downstream consumers — not via direct UI):

- market risk managers reviewing the day's investigation handoff list
- production control owners reviewing per-target trust outcomes

The orchestrator does not communicate with humans directly. Human escalation in v1 is the appearance of any `HOLD_*` handoff status in the returned handoff list, surfaced by a downstream consumer.

## Core principles

- workflow state, routing, gates, retries, and handoff only — no canonical trust or calculation logic
- one canonical run-state object per invocation
- deterministic challenge gate driven entirely by upstream typed fields
- explicit degraded, blocked, partial, and failed run-level outcomes
- replay by pinned `snapshot_id` and pinned candidate set
- typed propagation of upstream evidence; no orchestrator-owned evidence shape
- telemetry uses the shared contract; no module-local status mapping

## Trigger conditions

### Trigger event (v1)

A direct programmatic call to:

```python
def start_daily_run(
    as_of_date: date,
    snapshot_id: str,
    candidate_targets: tuple[NodeRef, ...],
    measure_type: MeasureType,
    *,
    risk_fixture_index: FixtureIndex | None = None,
    controls_fixture_index: ControlsIntegrityFixtureIndex | None = None,
) -> DailyRunResult:
```

### Trigger prerequisites

- `as_of_date` is a valid `date`
- `snapshot_id` is non-empty (pinned snapshots are mandatory in v1; latest-resolution is forbidden per ADR-002)
- `candidate_targets` is a non-empty tuple of `NodeRef` values; an empty tuple is a typed request validation failure
- `measure_type` is a `MeasureType` value supported by both `get_risk_summary` and the controls integrity service for v1
- the orchestrator does not infer `as_of_date` from a calendar; ADR-004 calendar primitives are exercised only by upstream services

### Forbidden triggers in v1

- cron, scheduler, file-watch, message-bus, or webhook entry points (deferred)
- multi-day batch entry points (deferred)
- a "run for all known targets" entry point (would require materiality logic)

## Workflow state model

### Run lifecycle

A single run has one terminal state. Once `start_daily_run` returns, the run is complete. There is no in-flight, suspended, resumable, or rehydrated state in v1. The returned `DailyRunResult` is the run's full persisted state.

### Run-level state object: `DailyRunResult`

Fields (all required unless noted; frozen typed model per ADR-001):

- `run_id` (str, deterministic — see "Run identity" below)
- `as_of_date` (date)
- `snapshot_id` (str, non-empty)
- `measure_type` (MeasureType)
- `candidate_targets` (tuple[NodeRef, ...], the input set, preserved order)
- `selected_targets` (tuple[NodeRef, ...], the post-readiness/selection set, preserved order)
- `target_results` (tuple[`TargetInvestigationResult`, ...], one per `selected_targets` entry, preserved order)
- `handoff` (tuple[`TargetHandoffEntry`, ...], one per `selected_targets` entry, preserved order)
- `readiness_state` (ReadinessState — `READY` | `BLOCKED`)
- `readiness_reason_codes` (tuple[str, ...], deduplicated, lexicographically ascending)
- `terminal_status` (TerminalRunStatus — `COMPLETED` | `COMPLETED_WITH_CAVEATS` | `COMPLETED_WITH_FAILURES` | `FAILED_ALL_TARGETS` | `BLOCKED_READINESS`)
- `degraded` (bool — true iff any selected target produced an `assessment_status == DEGRADED`)
- `partial` (bool — true iff at least one selected target produced a `ServiceError` and at least one produced an `IntegrityAssessment`)
- `orchestrator_version` (str, non-empty, pinned at module level)
- `generated_at` (datetime, deterministic — see "Replay and determinism")

### Per-target investigation object: `TargetInvestigationResult`

Fields:

- `node_ref` (NodeRef)
- `measure_type` (MeasureType)
- `outcome_kind` (OutcomeKind — `ASSESSMENT` | `SERVICE_ERROR`)
- `assessment` (IntegrityAssessment | None — present iff `outcome_kind == ASSESSMENT`)
- `service_error` (ServiceError | None — present iff `outcome_kind == SERVICE_ERROR`)

The orchestrator must not collapse, transform, or summarize the upstream typed object. It is propagated by reference (immutable nested model) only.

### Per-target handoff entry: `TargetHandoffEntry`

Fields:

- `node_ref` (NodeRef)
- `measure_type` (MeasureType)
- `handoff_status` (HandoffStatus — see "Challenge gate")
- `blocking_reason_codes` (tuple[ReasonCode, ...], propagated from `IntegrityAssessment.blocking_reason_codes` when present, else empty)
- `cautionary_reason_codes` (tuple[ReasonCode, ...], propagated from `IntegrityAssessment.cautionary_reason_codes` when present, else empty)
- `service_error_status_code` (str | None — populated iff `outcome_kind == SERVICE_ERROR`)

The handoff entry contains no orchestrator-originated reason codes. All codes are propagated from upstream typed outputs unchanged.

### Allowed transitions

Stages execute strictly in fixed order with no branching, retry, or parallelism in v1. There are no intermediate persisted states. Stage transitions are observable only via telemetry events.

### Terminal states

- `BLOCKED_READINESS` — readiness gate failed; no targets investigated
- `FAILED_ALL_TARGETS` — readiness passed; every selected target produced a `ServiceError`
- `COMPLETED_WITH_FAILURES` — readiness passed; at least one target produced a `ServiceError` and at least one produced an `IntegrityAssessment`
- `COMPLETED_WITH_CAVEATS` — readiness passed; all selected targets produced an `IntegrityAssessment`; at least one had `assessment_status == DEGRADED` or any non-`READY_FOR_HANDOFF` handoff status
- `COMPLETED` — readiness passed; every selected target produced `assessment_status == OK` and `handoff_status == READY_FOR_HANDOFF`

Terminal-status precedence (highest first; first match wins):

1. `BLOCKED_READINESS`
2. `FAILED_ALL_TARGETS`
3. `COMPLETED_WITH_FAILURES`
4. `COMPLETED_WITH_CAVEATS`
5. `COMPLETED`

## Workflow stages

Stages are executed in this fixed order. Each stage has explicit inputs, outputs, and forbidden actions. Stage names are stable identifiers (used in telemetry).

### Stage 1 — `intake`

- **Inputs:** caller arguments to `start_daily_run`
- **Outputs:** validated typed inputs, allocated `run_id`, `started_at` monotonic clock anchor
- **Behavior:** typed input validation only (per "Trigger prerequisites"). Constructs an internal in-progress state. Allocates a deterministic `run_id` (see "Run identity"). Emits one `intake` telemetry event.
- **Forbidden:** any business logic; any I/O beyond the caller-provided fixture indices; any silent input coercion.

### Stage 2 — `readiness_gate`

- **Inputs:** `as_of_date`, `snapshot_id`, `candidate_targets` (first element used as canary), `measure_type`, fixture indices
- **Outputs:** `readiness_state`, `readiness_reason_codes`
- **Behavior:** verifies the snapshot resolves and the canary candidate is addressable in the pinned snapshot, by calling `get_risk_summary` for the first `candidate_targets` entry with the same `as_of_date`, `measure_type`, and `snapshot_id`. Readiness rule:
  - if the call returns a typed `RiskSummary` (any `SummaryStatus`), readiness is `READY` and `readiness_reason_codes` is empty
  - if the call returns a `ServiceError` with `status_code` in `{MISSING_SNAPSHOT, UNSUPPORTED_MEASURE}`, readiness is `BLOCKED` and `readiness_reason_codes = (status_code,)`
  - if the call returns a `ServiceError` with `status_code == MISSING_NODE`, readiness is `READY` and `readiness_reason_codes = ("READINESS_CANARY_MISSING_NODE",)` (the canary's absence does not block the run; per-target selection handles missing nodes)
- **Forbidden:** invoking the controls integrity service or any walker; running any per-target loop; recomputing the snapshot; falling back to latest snapshot.

If `readiness_state == BLOCKED`, the orchestrator skips Stages 3–8, runs Stage 9, and returns a `DailyRunResult` with `terminal_status = BLOCKED_READINESS`, `selected_targets = ()`, `target_results = ()`, `handoff = ()`.

### Stage 3 — `target_selection`

- **Inputs:** `candidate_targets`, `as_of_date`, `snapshot_id`, `measure_type`, fixture indices
- **Outputs:** `selected_targets` (tuple[NodeRef, ...], preserved input order)
- **Behavior:** v1 selection is a pass-through with one deterministic filter:
  - for each `node_ref` in `candidate_targets`, call `get_risk_summary(node_ref, as_of_date, measure_type, snapshot_id=snapshot_id, ...)`
  - include the `node_ref` in `selected_targets` when the call returns a `RiskSummary` of any `SummaryStatus`
  - exclude the `node_ref` only when the call returns a `ServiceError` with `status_code == MISSING_NODE`
  - any other `ServiceError` from `get_risk_summary` (for example `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`) raises `RuntimeError("readiness invariant violated after gate passed")`; this is a programmer error because it should already have been caught by Stage 2
- **Forbidden:** any materiality, scoring, ranking, threshold, magnitude, volatility, or risk-change rule; any input reordering; any deduplication beyond the upstream pass-through; any walker calls; any inference of materiality from `RiskSummary` fields.

### Stage 4 — `target_routing`

- **Inputs:** `selected_targets`
- **Outputs:** an internal routing decision per target (always: route to `data_controller.assess_integrity`)
- **Behavior:** in v1 the routing decision is a constant: every selected target is routed to the data controller walker exactly once. Routing is recorded only as part of telemetry context.
- **Forbidden:** routing to any other walker; conditional routing rules; partial routing.

### Stage 5 — `investigation`

- **Inputs:** `selected_targets`, `as_of_date`, `snapshot_id`, `measure_type`, fixture indices
- **Outputs:** internal per-target `IntegrityAssessment | ServiceError` collected in `selected_targets` order
- **Behavior:** for each `node_ref` in `selected_targets`, call `data_controller.assess_integrity(node_ref, measure_type, as_of_date, snapshot_id, risk_fixture_index=..., controls_fixture_index=...)` exactly once. Calls are sequential in `selected_targets` order. The orchestrator does not catch exceptions raised by the walker; per PRD-4.1 the walker propagates `ValueError` for invalid inputs unchanged. Any such `ValueError` must escape the orchestrator unchanged (these are programmer-input errors, not workflow outcomes).
- **Forbidden:** parallel execution in v1; per-target retries; suppression of any `ValueError`; calling any other walker or the controls integrity service directly; any reinterpretation of the typed return value.

### Stage 6 — `synthesis`

- **Inputs:** the per-target `IntegrityAssessment | ServiceError` outcomes from Stage 5
- **Outputs:** `target_results` (tuple[`TargetInvestigationResult`, ...], same length and order as `selected_targets`)
- **Behavior:** structural collation only. For each outcome, construct one `TargetInvestigationResult` with `outcome_kind` set to `ASSESSMENT` or `SERVICE_ERROR` and the upstream typed object propagated by reference into the corresponding nested field.
- **Forbidden:** aggregation of trust state across targets; computation of any run-level "trust verdict"; deduplication, sorting, or reordering of upstream reason codes; substitution of any upstream typed field with a derived value; narrative or prose generation; cross-target inference.

### Stage 7 — `challenge`

- **Inputs:** `target_results`
- **Outputs:** `handoff` (tuple[`TargetHandoffEntry`, ...], same length and order as `selected_targets`)
- **Behavior:** rule-based deterministic gate, applied per target independently. For each `TargetInvestigationResult`, compute `handoff_status` per the precedence in "Challenge gate" below. Propagate the upstream `blocking_reason_codes` and `cautionary_reason_codes` unchanged when an `IntegrityAssessment` is present.
- **Forbidden:** human-in-the-loop interaction; reading any external configuration; introducing override flags; cross-target rules; any rule that depends on fields not already present in `IntegrityAssessment` or `ServiceError`.

### Stage 8 — `handoff`

- **Inputs:** `handoff` entries from Stage 7
- **Outputs:** the same `handoff` tuple, attached to the in-progress run state
- **Behavior:** structural assembly only. v1 does not push to any external system, queue, or downstream consumer. The `handoff` tuple is part of the returned `DailyRunResult`.
- **Forbidden:** any I/O; any external notification; any prioritization or filtering of handoff entries; any scoring.

### Stage 9 — `persist`

- **Inputs:** the in-progress run state
- **Outputs:** the final, validated `DailyRunResult` returned by `start_daily_run`
- **Behavior:** computes `terminal_status` per the precedence in "Terminal states", computes `degraded` and `partial` per their definitions, sets `generated_at` per "Replay and determinism", and constructs the final frozen `DailyRunResult` model. Emits one terminal `daily_run_complete` telemetry event.
- **Forbidden:** writing to any durable store; writing to any file; mutating the run state after construction; recomputing any upstream value.

## Routing rules

### Walker routing (v1)

| Selected target outcome path | Walker invoked | Calls per target |
| --- | --- | --- |
| Any `node_ref` in `selected_targets` | `data_controller.assess_integrity` | exactly one |

No other walker is invoked. No conditional routing. No skip-routing.

### Control gates (v1)

There are exactly two control gates in v1:

1. **Readiness gate** (Stage 2) — blocks the entire run on snapshot or measure-level unavailability.
2. **Challenge gate** (Stage 7) — assigns a per-target `handoff_status` from upstream typed fields.

No other gates. No third-party gate. No cross-stage gate.

## Challenge gate

### `HandoffStatus` vocabulary (v1)

- `READY_FOR_HANDOFF`
- `PROCEED_WITH_CAVEAT`
- `HOLD_BLOCKING_TRUST`
- `HOLD_UNRESOLVED_TRUST`
- `HOLD_INVESTIGATION_FAILED`

### Per-target gate rules (precedence top-to-bottom; first match wins)

For a given `TargetInvestigationResult`:

1. if `outcome_kind == SERVICE_ERROR` → `HOLD_INVESTIGATION_FAILED`
2. else if `assessment.trust_state == BLOCKED` → `HOLD_BLOCKING_TRUST`
3. else if `assessment.trust_state == UNRESOLVED` → `HOLD_UNRESOLVED_TRUST`
4. else if `assessment.assessment_status == DEGRADED` → `PROCEED_WITH_CAVEAT`
5. else if `assessment.trust_state == CAUTION` and `assessment.assessment_status == OK` → `PROCEED_WITH_CAVEAT`
6. else if `assessment.trust_state == TRUSTED` and `assessment.assessment_status == OK` → `READY_FOR_HANDOFF`

These rules read only `trust_state` and `assessment_status` from the upstream typed assessment. They introduce no orchestrator-owned trust semantics.

### Forbidden challenge behaviors in v1

- consulting any field beyond `trust_state` and `assessment_status` for status assignment (other than `ServiceError.status_code`, which is propagated only into `service_error_status_code`, not into `handoff_status`)
- emitting orchestrator-originated reason codes
- collapsing or merging upstream reason codes
- run-wide aggregate "challenge verdict" beyond `terminal_status`
- override capture, signed escalation, dispute capture
- consulting any human input

## Human escalation / handoff boundary

- The orchestrator never solicits human input in v1.
- Human escalation is the appearance of any `HOLD_*` `handoff_status` in the returned `handoff` tuple. Surfacing that to humans is a downstream consumer responsibility (not built in v1).
- The orchestrator does not approve, reject, dismiss, or sign off any target outcome.
- Governance approval lifecycle, committee pack assembly, breach approval workflow, and analyst override capture are out of scope.

## Run identity

`run_id` is a deterministic string computed at intake from the canonical inputs that fully determine a replay-equivalent run.

`run_id` derivation (normative, v1):

- input components, in fixed order:
  - `as_of_date` (ISO date string)
  - `snapshot_id`
  - `measure_type.value`
  - the tuple of `candidate_targets`, each serialized as the canonical `node_ref_log_dict` shape from `src.shared.telemetry.operation_log`
  - `orchestrator_version` (module-level constant pinned in `src/orchestrators/daily_risk_investigation/`) <!-- drift-ignore -->
- the components are JSON-serialized with sorted keys at every dict level
- `run_id = "drun_" + sha256(serialized_components_utf8).hexdigest()`

The exact serialization helper is an implementation detail of WI-5.1.1 but must be deterministic, replay-stable, and covered by unit tests. The `drun_` prefix is normative and stable across versions.

`run_id` does not include `generated_at` or any wall-clock value.

## Replay and determinism

Aligned with ADR-002 (replay and snapshot model):

- `snapshot_id` is mandatory in v1; the orchestrator never accepts `snapshot_id=None` and never silently resolves a snapshot at run time
- equal `(as_of_date, snapshot_id, candidate_targets, measure_type, orchestrator_version, fixture_index_state)` inputs must produce equal `DailyRunResult` values, field-for-field, across runs
- `generated_at` is deterministic from snapshot context only: it must equal the maximum `generated_at` across the per-target `IntegrityAssessment` outputs returned by the walker in Stage 5; if `selected_targets` is empty (readiness blocked) or every target produced a `ServiceError`, `generated_at` falls back to `datetime.combine(as_of_date, time(hour=18, minute=0, tzinfo=timezone.utc))`, which matches the upstream service's deterministic anchor and avoids introducing a new wall-clock dependency
- `orchestrator_version` is pinned at module level and bumped only by an explicit work item; any contract change to `DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, the `HandoffStatus` vocabulary, the `TerminalRunStatus` vocabulary, or the per-target gate rules requires a version bump
- the orchestrator must not introduce its own snapshot resolver or its own business-day primitive (ADR-004 is satisfied entirely by upstream services)

## Evidence and trace propagation

Aligned with ADR-003 (evidence and trace model):

- `TargetInvestigationResult.assessment` carries the upstream `IntegrityAssessment` unchanged, including all `ControlCheckResult` entries with their `evidence_refs` and the `snapshot_id` / `data_version` / `service_version` fields
- `TargetHandoffEntry.blocking_reason_codes` and `cautionary_reason_codes` are the same tuples returned by the upstream service (no reshaping, no deduplication beyond the upstream contract, no orchestrator-originated codes)
- the orchestrator must not strip, modify, supplement, or summarize any upstream evidence reference
- the orchestrator does not introduce a new evidence shape, a new trace envelope, or a new correlation header in v1
- `run_id` serves as the orchestrator-level correlation identifier in telemetry events; it is not embedded into upstream typed objects

## Telemetry requirements

Aligned with `docs/shared_infra/telemetry.md`:

- the orchestrator must use `src.shared.telemetry.emit_operation` for all structured operation events
- the orchestrator must not import from `agent_runtime`
- the orchestrator must not redefine status-to-level mapping (it is owned by the shared telemetry implementation)
- payload discipline: no raw fixtures, no full upstream typed objects, no `IntegrityAssessment` payloads in log records — only low-cardinality identifiers, counts, and canonical statuses
- `include_trace_context=False` is acceptable in v1 (consistent with the `data_controller` walker emission pattern); a future WI may opt in to OpenTelemetry context

### Required events (v1)

Exactly the following events must be emitted per run, each with the listed minimum context:

| Event `operation` | Status field source | Required context fields (in addition to `operation`, `status`, `duration_ms`) |
| --- | --- | --- |
| `daily_run.intake` | `OK` | `run_id`, `as_of_date`, `snapshot_id`, `measure_type`, `candidate_count` |
| `daily_run.readiness_gate` | `OK` when `readiness_state == READY`; otherwise the canary call's `ServiceError.status_code` (one of `MISSING_SNAPSHOT`, `UNSUPPORTED_MEASURE`) | `run_id`, `as_of_date`, `snapshot_id`, `readiness_state`, `readiness_reason_codes` |
| `daily_run.target_selection` | `OK` | `run_id`, `candidate_count`, `selected_count`, `excluded_missing_node_count` |
| `daily_run.investigation` | `OK` | `run_id`, `selected_count`, `assessment_count`, `service_error_count` |
| `daily_run.challenge` | `OK` | `run_id`, `ready_for_handoff_count`, `proceed_with_caveat_count`, `hold_blocking_trust_count`, `hold_unresolved_trust_count`, `hold_investigation_failed_count` |
| `daily_run.handoff` | `OK` | `run_id`, `handoff_count` |
| `daily_run_complete` | mapped canonical status derived from `terminal_status` (`COMPLETED` → `OK`; `COMPLETED_WITH_CAVEATS` → `DEGRADED`; `COMPLETED_WITH_FAILURES` → `PARTIAL`; `FAILED_ALL_TARGETS` → `DEGRADED`; `BLOCKED_READINESS` → `DEGRADED`) | `run_id`, `as_of_date`, `snapshot_id`, `terminal_status`, `degraded`, `partial`, `selected_count`, `assessment_count`, `service_error_count` |

The status mapping above is normative. Every value emitted in the `status` field of an orchestrator telemetry event must be one of the canonical statuses already supported by `_INFO_STATUSES` or `_WARNING_STATUSES` in `src.shared.telemetry.operation_log` (no new status strings). The raw `terminal_status` enum value (for example `COMPLETED_WITH_CAVEATS`) is emitted only as a context field on `daily_run_complete`, never as the canonical `status`.

Stages `target_routing`, `synthesis`, and `persist` intentionally do not emit standalone events in v1: routing is a constant decision in the single-walker scope, synthesis is structural collation only, and persistence completion is captured by the terminal `daily_run_complete` event. Adding separate events for these stages requires a PRD update.

If `readiness_state == BLOCKED`, the orchestrator emits `daily_run.intake`, `daily_run.readiness_gate`, and `daily_run_complete` only. Stages 3–8 emit no telemetry in the blocked path.

### Adoption matrix

Once the telemetry slice (WI-5.1.3) is implemented and merged, `docs/shared_infra/adoption_matrix.md` must be updated:

- the `src/orchestrators/` row moves from `Status: planned` to `Status: adopted`
- `Notes` should reference: telemetry uses `src.shared.telemetry.emit_operation`; daily-run operation-log slice is WI-5.1.3; no module-local duplicate status mapping

This is part of the v1 PRD's required outcome and must not be deferred to a follow-up phase.

## Error handling and degraded cases

| Condition | Surfaced as | Run outcome |
| --- | --- | --- |
| typed input validation failure (invalid `node_ref`, empty `candidate_targets`, empty `snapshot_id`, etc.) | `ValueError` (or the canonical `RequestValidationFailure` from `src.shared` if used by upstream services for the same input shape) raised by intake stage; never returned inside `DailyRunResult` | run does not complete; no `DailyRunResult` returned |
| `MISSING_SNAPSHOT` or `UNSUPPORTED_MEASURE` from readiness canary | `readiness_state = BLOCKED`; matching reason code in `readiness_reason_codes` | `terminal_status = BLOCKED_READINESS` |
| `MISSING_NODE` for the readiness canary only | `readiness_state = READY`, `readiness_reason_codes = ("READINESS_CANARY_MISSING_NODE",)` | run continues normally; per-target selection still filters that node out |
| `MISSING_NODE` for any candidate during selection | candidate excluded from `selected_targets`; tracked via `excluded_missing_node_count` telemetry field | run continues |
| any unexpected `ServiceError` from `get_risk_summary` after readiness passed | `RuntimeError("readiness invariant violated after gate passed")` | run aborts (programmer error) |
| `ServiceError` from `data_controller.assess_integrity` for a target | `outcome_kind = SERVICE_ERROR`; `handoff_status = HOLD_INVESTIGATION_FAILED` | per-target only; run continues |
| `ValueError` from `data_controller.assess_integrity` for invalid inputs | propagated unchanged | run aborts (programmer error) |
| `IntegrityAssessment` with `assessment_status == DEGRADED` | per-target outcome captured unchanged; `degraded = True` at run level | run completes; `terminal_status = COMPLETED_WITH_CAVEATS` (or higher per precedence) |
| mixed: at least one assessment + at least one service error | `partial = True` at run level | `terminal_status = COMPLETED_WITH_FAILURES` |
| every selected target returns `ServiceError` | `partial = False` (no successful target); `degraded = False` | `terminal_status = FAILED_ALL_TARGETS` |
| every selected target returns `IntegrityAssessment` with `assessment_status == OK`, `trust_state == TRUSTED` | clean path | `terminal_status = COMPLETED` |

### Retry semantics (v1)

- the orchestrator performs **no automatic retries**: each upstream call is invoked exactly once per stage per target
- per-target failures (`ServiceError`) propagate into `HOLD_INVESTIGATION_FAILED` and never trigger a re-attempt within the same run
- run-level failures (`BLOCKED_READINESS`, `FAILED_ALL_TARGETS`) terminate the run; the caller may invoke `start_daily_run` again with corrected inputs
- because the run is fully replayable from `(as_of_date, snapshot_id, candidate_targets, measure_type)`, "retry" is the caller's responsibility and is equivalent to re-invoking the entry point
- cross-run retry queues, exponential backoff, dead-letter handling, and durable retry state are explicitly out of scope

## Security and control constraints

### Allowed actions

- read-only calls into `src.modules.risk_analytics.get_risk_summary`
- read-only calls into `src.walkers.data_controller.assess_integrity`
- in-memory construction and return of typed `DailyRunResult`
- structured telemetry emission via `src.shared.telemetry.emit_operation`

### Forbidden actions

- writing to any durable store (database, filesystem, object store, message queue)
- imports from `agent_runtime`
- imports from private submodules of `src/modules/controls_integrity/` or `src/modules/risk_analytics/` (only documented public surfaces)
- direct calls to `src.modules.controls_integrity.get_integrity_assessment` (must go through the `data_controller` walker so the architecture boundary is exercised end-to-end)
- introducing module-level mutable state beyond pinned version constants
- introducing parallelism, threading, or asyncio in v1

## Acceptance criteria

### Functional

- `start_daily_run` exists and is importable from the `daily_risk_investigation` orchestrator package
- `start_daily_run` returns a `DailyRunResult` for every well-formed input, except inputs that fail typed validation (which raise)
- all nine stages execute in fixed order; stages 3–8 are skipped when readiness is `BLOCKED`
- per-target challenge gate produces the documented `handoff_status` for every combination of `(outcome_kind, trust_state, assessment_status)` reachable via the existing controls integrity fixtures
- terminal-status precedence is enforced in the order documented above
- `readiness_state` and `readiness_reason_codes` are populated exactly per the readiness rules; readiness canary `MISSING_NODE` does not block the run

### Contract

- `DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, `HandoffStatus`, `TerminalRunStatus`, `ReadinessState`, and `OutcomeKind` are typed (Pydantic models / `StrEnum`) per ADR-001
- all enum vocabularies are exactly the values listed in this PRD; no extra members
- `IntegrityAssessment` and `ServiceError` are propagated unchanged into `TargetInvestigationResult`
- `blocking_reason_codes` and `cautionary_reason_codes` in `TargetHandoffEntry` are byte-for-byte equal to the upstream tuples when an assessment is present
- `run_id` is deterministic per the documented derivation; identical inputs produce identical `run_id`

### Architecture

- orchestrator package lives at `src/orchestrators/daily_risk_investigation/` and exposes only the public entry point and result types via its `__init__.py` <!-- drift-ignore -->
- orchestrator imports the controls integrity surface only via the `data_controller` walker (no direct service import)
- orchestrator imports `get_risk_summary` from the public `src.modules.risk_analytics` surface only
- `src/orchestrators/README.md` is updated to reflect that `daily_risk_investigation/` is the first implemented orchestrator (single-line note; no scope expansion)

### Replay

- replay test: equal inputs across two invocations produce equal `DailyRunResult` instances (equal under Pydantic model equality)
- `generated_at` is deterministic per the documented rule; no wall-clock leakage
- `run_id` derivation has a unit test pinning a known input set to a known hex digest

### Telemetry

- every required event is emitted exactly once per run (subject to the BLOCKED-readiness exception)
- no unexpected events are emitted
- payload contracts match the table above; no `IntegrityAssessment` or `ServiceError` payloads appear in log records
- `src/orchestrators/` row in `docs/shared_infra/adoption_matrix.md` reflects `adopted` after WI-5.1.3 lands

### Out of scope guarded

- no orchestrator-owned trust logic, materiality logic, retry loop, durable persistence, second walker, UI surface, governance approval flow, or new typed evidence shape appears in the v1 implementation

## Test intent

### Unit tests (WI-5.1.1 and WI-5.1.2)

- typed contract construction tests for `DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, and the four enums
- input validation tests for `start_daily_run` (empty `snapshot_id`, empty `candidate_targets`, missing required arguments)
- stage-ordering test (instrumented via injected fakes or telemetry capture; readiness-blocked path exercises the skip behavior)
- challenge gate truth-table test covering every documented `(outcome_kind, trust_state, assessment_status)` combination
- terminal-status precedence test covering each documented precedence transition

### Integration tests (WI-5.1.2)

- one happy-path run over a small candidate set with the existing `controls_integrity` and `risk_analytics` fixture indices, asserting `terminal_status == COMPLETED` (or `COMPLETED_WITH_CAVEATS` if the smallest available fixture induces it; the PRD does not require the existence of a fully-clean fixture)
- one run that exercises `MISSING_NODE` exclusion in selection
- one run that exercises `HOLD_INVESTIGATION_FAILED` propagation
- one run that exercises `BLOCKED_READINESS`

### Replay tests (WI-5.1.4)

- two-invocation determinism test on the happy path
- pinned `run_id` digest test on a fixed input
- `generated_at` determinism test

### Telemetry tests (WI-5.1.3)

- caplog-style assertion that each required event is emitted exactly once per run with the documented context fields, using the existing shared-telemetry test patterns from `src/modules/controls_integrity/` and `src/walkers/data_controller/`
- assertion that no `IntegrityAssessment` or `ServiceError` payload leaks into log records
- assertion that `agent_runtime` is not imported transitively from the orchestrator package

## Issue decomposition guidance

This PRD must be implemented as a sequence of bounded slices. PM / Issue Planner derives concrete WIs from this guidance.

### Suggested sequence

1. **WI-5.1.1 — Orchestrator skeleton and typed contracts**
   - create `src/orchestrators/daily_risk_investigation/` package with `__init__.py` <!-- drift-ignore -->
   - define `DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, `HandoffStatus`, `TerminalRunStatus`, `ReadinessState`, `OutcomeKind` (typed-schema approach per ADR-001)
   - define `start_daily_run` entry-point signature and `run_id` derivation only; no stage execution behavior yet
   - unit tests for contract shapes and `run_id` determinism
   - update `src/orchestrators/README.md` minimal one-line note
   - depends on: PRD-4.1 walker scaffolding (already merged), PRD-1.1-v2 service (already merged), this PRD merged on `main`
   - shared-infra impact: declared but not yet adopted (telemetry slice is WI-5.1.3)

2. **WI-5.1.2 — Stage execution end-to-end**
   - implement Stages 1–9 per this PRD
   - implement readiness gate, target selection (pass-through with `MISSING_NODE` filter), routing, investigation, synthesis, challenge gate, handoff, persist
   - implement terminal-status, `degraded`, `partial`, `generated_at` derivation
   - unit + integration tests per "Test intent"
   - depends on: WI-5.1.1
   - no telemetry yet (added in WI-5.1.3)

3. **WI-5.1.3 — Telemetry adoption + adoption matrix flip**
   - add `emit_operation` calls for every required event per the telemetry table
   - assert payload discipline (no `IntegrityAssessment` payloads in logs)
   - update `docs/shared_infra/adoption_matrix.md` `src/orchestrators/` row from `planned` → `adopted` with WI-5.1.3 note
   - telemetry tests per "Test intent"
   - depends on: WI-5.1.2

4. **WI-5.1.4 — Replay determinism tests**
   - add the explicit replay test set described above (two-invocation equality, pinned `run_id` digest, `generated_at` determinism)
   - depends on: WI-5.1.3 (so replay tests cover the telemetry-included implementation)

### Sequencing notes for PM

- WI-5.1.1 may be sized as a single small slice; if PM/Issue Planner judges it small enough, it can be merged with WI-5.1.2 into one WI, but the contracts must land first within that combined slice
- WI-5.1.3 is the gate for the adoption-matrix flip; it must not be merged until telemetry payload tests pass
- WI-5.1.4 may be split across the previous WIs at PM discretion if the team prefers replay tests to land alongside the slice that implements them
- no WI in this sequence is permitted to widen scope beyond this PRD; any expansion (second walker, materiality logic, durable persistence, human handoff) requires a new PRD

### Out of decomposition (will not be issued under this PRD)

- materiality / target-selection logic
- second walker integration
- durable persistence
- human-in-the-loop challenge UI
- governance approval lifecycle
- monthly committee orchestration

## Reviewer checklist

- workflow state, routing, gates, retries, and handoff are the orchestrator's only concerns; no canonical trust or calculation logic appears in the implementation
- no orchestrator-originated trust state, reason code, evidence shape, or materiality rule
- per-target challenge gate reads only `trust_state`, `assessment_status`, and `ServiceError.status_code`
- `IntegrityAssessment` and `ServiceError` are propagated unchanged into `TargetInvestigationResult`
- `snapshot_id` is mandatory; no latest-snapshot fallback
- `run_id` derivation is deterministic and excludes wall-clock values
- `generated_at` derivation is deterministic per the documented rule
- telemetry uses `src.shared.telemetry.emit_operation` exclusively; no `agent_runtime` import; no module-local status mapping; no `IntegrityAssessment` payloads in log records
- adoption matrix is updated to `adopted` once telemetry slice merges
- backtick-wrapped paths to the planned `src/orchestrators/daily_risk_investigation/` package are linked to WI-5.1.1 in the header per the reference-integrity convention used by PRD-4.1 <!-- drift-ignore -->
- out-of-scope items have not silently leaked into v1
- PRD-1.1-v2, PRD-2.1, and PRD-4.1 contracts are cross-referenced, not restated or altered

## Open questions (v2+ only — none block v1)

- **Materiality determination ownership.** v1 requires the caller to supply `candidate_targets`. v2+ must answer: does materiality live in a deterministic service (e.g. a "material change" service over `RiskSummary` / `RiskChangeProfile` outputs), in a dedicated walker, or in the orchestrator (least preferred)? An ADR may be required.
- **Multi-walker routing.** v1 routes every selected target to `data_controller` only. v2+ will need to route to additional walkers (quant, time-series, market-context, controls-change, governance-reporting, critic-challenge). The routing rule shape (per-target, per-trust-state, per-measure-type) is undecided.
- **Human-in-the-loop challenge.** v1 challenge is rule-based and surfaces `HOLD_*` statuses passively. v2+ may add operator override capture, signed escalation, dispute capture, or analyst review console integration. None of these belong in the orchestrator without explicit PRD scope.
- **Durable persistence.** v1 returns the run state by value. v2+ may require a persistence backend; an ADR is likely required to choose the storage model and to specify retention, indexability, and replay-store contracts.
- **Cross-run retry semantics.** v1 has no retries. v2+ may introduce retry queues, scheduled re-runs, or partial-replay; this should land in a separate PRD with explicit semantics.
- **Trigger surface.** v1 is programmatic only. Cron / scheduler / event-bus / file-watch triggers and their idempotency semantics are deferred.
- **Trace context propagation.** v1 emits telemetry with `include_trace_context=False`. A future WI may opt in to OpenTelemetry context propagation across orchestrator, walker, and service layers; this likely requires a shared-infra update.
- **`run_id` collision and rotation policy.** v1 uses a deterministic SHA-256 over canonical inputs. If a v2+ caller wants to distinguish two replays of the same input set, the derivation will need a non-replayable component; the trade-off against ADR-002 must be made explicit at that point.

## AI agent instructions

### Coding agent

- implement exactly what this PRD specifies; do not add stages, gates, status values, walker integrations, or trust rules not listed here
- consume `IntegrityAssessment | ServiceError` only via `data_controller.assess_integrity`; do not import `get_integrity_assessment` directly
- consume `RiskSummary | ServiceError` only via the public `src.modules.risk_analytics.get_risk_summary` surface
- use `src.shared.telemetry.emit_operation` exactly per the telemetry table; do not invent new status strings
- pin `orchestrator_version` at module level; do not use a wall-clock value in `run_id`
- if any test reveals an ambiguity in the PRD, stop and route the question back through PM/PRD; do not invent semantics

### Review agent

- check that the orchestrator does not own trust, materiality, or calculation logic
- check that all per-target gate decisions read only the documented upstream fields
- check that `IntegrityAssessment` and `ServiceError` are propagated unchanged
- check telemetry payload discipline and adoption-matrix update
- check that no `agent_runtime` import has crept in
- check `run_id` and `generated_at` determinism tests exist and pin specific values
- flag any scope creep (additional walker, materiality rule, persistence backend, UI rendering) explicitly as out of scope

### PM agent

- treat WI-5.1.1, WI-5.1.2, WI-5.1.3, and WI-5.1.4 as the bounded sequence under this PRD
- do not assign any WI under this PRD that widens scope beyond the in-scope list
- the adoption-matrix flip is part of v1 acceptance and must not be deferred

# PRD-2.1: Controls and Production Integrity Assessment Service

## Header

- **PRD ID:** PRD-2.1
- **Title:** Controls and Production Integrity Assessment Service
- **Phase:** Phase 2
- **Status:** Ready for PM readiness assessment
- **Module:** Controls & Production Integrity
- **Type:** Deterministic service
- **Primary owner:** Technical Owner, Controls & Production Integrity
- **Business owner:** Market Risk Controls Owner
- **Control owner:** Risk Data / Production Controls Owner
- **Related components:** Data Controller Walker, Daily Risk Investigation orchestrator, Risk Analytics module
- **Dependencies:** PRD-1.1 Risk Summary Service v2, ADR-001, ADR-002, ADR-003, ADR-004

## Purpose

Provide the canonical deterministic service that answers one operationally critical question before deeper interpretation proceeds:

- can the observed risk signal be trusted enough for downstream investigation?

This service supports the operating-model step "confirm the data is trustworthy enough" before walkers or orchestrators attempt market, control, or governance interpretation.

## Why this is the Phase 2 slice

Phase 1 established typed, replayable risk facts for one node, measure, and date. The next highest-value governed step is not more narrative or orchestration. It is trust gating.

This slice is chosen first within Phase 2 because it:

- directly gates downstream investigation quality
- reuses the Phase 1 target identity, snapshot pinning, and shared error-envelope conventions
- supports the Data Controller Walker charter without letting the walker invent canonical trust logic
- stays narrower and more implementation-ready than a first FRTB / PLA control slice, which would require additional regulatory-control semantics in the same pass

FRTB / PLA controls remain part of the broader Phase 2 roadmap, but they are explicitly out of scope for this PRD and should be handled as a later Phase 2 PRD.

## Supported process context

This PRD supports:

- daily risk monitoring
- investigation of risk changes
- controls and production-integrity screening before explanation

It does not provide governance sign-off, remediation, or regulatory-capital interpretation.

## In scope

- deterministic trust assessment for one `node_ref`, `measure_type`, and `as_of_date`
- reuse of Phase 1 hierarchy and snapshot context semantics
- assessment of required control dimensions:
  - freshness
  - completeness
  - lineage
  - reconciliation
  - publication readiness
- explicit trust-state classification for downstream consumption
- explicit false-signal-risk classification
- typed check-level results with reason codes and evidence references
- replay by pinned `snapshot_id`
- fixture-driven implementation and replay tests

## Out of scope

- FRTB PLA, HPL, RTPL, backtesting, or desk regulatory status
- market-risk methodology explain or contributor decomposition
- remediation workflow, approvals, or incident ticket lifecycle
- free-form narrative generation
- direct ingestion from raw operational systems in v1
- batch ranking across many nodes
- historical trend analysis of trust-state over time
- UI rendering
- walker logic
- orchestrator routing logic
- any redesign of Phase 1 risk-summary contracts or status vocabulary

## Users and consumers

Primary consumers:

- Data Controller Walker
- Daily Risk Investigation orchestrator
- Governance / Reporting Walker

Secondary consumers:

- analyst review UI
- replay harness
- deterministic fixtures and tests

Human users influenced by this output:

- market risk managers deciding whether deeper investigation is safe
- production control owners deciding whether a case is operationally contaminated

## Core principles

- deterministic trust logic, not walker judgment
- one canonical trust answer per target and snapshot context
- explicit degraded and unresolved states
- no free-text evidence substitution
- replayable by pinned snapshot and resolved request context
- trust-state is distinct from risk magnitude or risk explanation

## Canonical concepts

### Target alignment

The assessment target uses the same typed `node_ref` and `measure_type` concepts established by PRD-1.1.

The service does not create a new free-text target identity model.

### Control normalization boundary

This service consumes canonical normalized control records. It does not derive trust directly from raw timestamps, row counts, or external-system payloads in v1.

Upstream control feeds must already normalize each required check into a deterministic check record.

For check types whose upstream determination depends on business-day semantics, including `FRESHNESS` and `PUBLICATION_READINESS`, the normalized control record must already reflect the shared business-day primitive governed by ADR-004. This service must not implement independent business-day or holiday logic.

Fixture and replay artifacts must pin the calendar basis used to produce those normalized check records.

### Normalized control record prerequisite contract

This PRD does not scope raw operational-feed normalization work, but it does require one canonical upstream normalized record shape per required check.

For v1, the service assumes exactly one uniqueness-resolved normalized control record per:

- `node_ref`
- `measure_type`
- `as_of_date`
- resolved `snapshot_id`
- `check_type`

Minimum required fields on each normalized control record are:

- `node_ref`
- `measure_type`
- `as_of_date`
- `snapshot_id`
- `check_type`
- `check_state`
- `reason_codes`
- `evidence_refs`
- `is_row_degraded`

If upstream data produces duplicate rows for the same uniqueness key, that is a normalization defect outside this service. This service must not invent a deduplication or winner-selection policy.

### Required check set

Every returned assessment is defined over exactly these check types:

- `FRESHNESS`
- `COMPLETENESS`
- `LINEAGE`
- `RECONCILIATION`
- `PUBLICATION_READINESS`

No other check type may be treated as required in v1.

### Trust state

Allowed values:

- `TRUSTED`
- `CAUTION`
- `BLOCKED`
- `UNRESOLVED`

### False-signal risk

Allowed values:

- `LOW`
- `MEDIUM`
- `HIGH`
- `UNKNOWN`

### Check state

Allowed values for each normalized control check:

- `PASS`
- `WARN`
- `FAIL`
- `UNKNOWN`

### Assessment status

Allowed values:

- `OK`
- `DEGRADED`

`assessment_status` describes the integrity of the returned assessment object itself. It does not replace `trust_state`.

## Inputs

### Required inputs

- `node_ref`
- `measure_type`
- `as_of_date`

### Optional inputs

- `snapshot_id`

### Input rules

- `node_ref` must use the Phase 1 typed hierarchy address and scope semantics unchanged
- `measure_type` must use the Phase 1 supported measure enum unchanged
- all Phase 1 `MeasureType` values are in scope for this service unchanged; `measure_type` remains part of canonical request identity and must not introduce a new service-specific filtering model
- if `snapshot_id` is provided, it must be non-empty and must resolve to a snapshot whose `as_of_date` equals `as_of_date`
- if `snapshot_id` is omitted, the service resolves the canonical snapshot for `as_of_date`
- control records must be resolved in the same pinned snapshot context as the risk target
- the service must not silently fall back from a pinned `snapshot_id` to latest-available behavior

## Outputs

### Primary output: `IntegrityAssessment`

Fields:

- `node_ref`
- `node_level`
- `hierarchy_scope`
- `legal_entity_id`
- `measure_type`
- `as_of_date`
- `trust_state`
- `false_signal_risk`
- `assessment_status`
- `blocking_reason_codes`
- `cautionary_reason_codes`
- `check_results`
- `snapshot_id`
- `data_version`
- `service_version`
- `generated_at`

### Nested output: `ControlCheckResult`

Fields:

- `check_type`
- `check_state`
- `reason_codes`
- `evidence_refs`

### Nested output: `EvidenceRef`

Fields:

- `evidence_type`
- `evidence_id`
- `source_as_of_date`
- `snapshot_id`

`EvidenceRef` is a typed nested object in this PRD so the service can satisfy ADR-003 without using prose-only evidence. A repo-wide shared evidence object is still a cross-module gap and is called out explicitly below.

## Canonical schemas

### `IntegrityAssessment`

Validation rules:

- `node_level`, `hierarchy_scope`, and `legal_entity_id` must mirror `node_ref` exactly, following the Phase 1 convention
- `blocking_reason_codes` and `cautionary_reason_codes` must be tuples of stable machine-readable reason codes, not prose paragraphs
- `blocking_reason_codes` and `cautionary_reason_codes` must be deduplicated and deterministically ordered
- `check_results` must contain exactly one result for each required check type
- `check_results` must be returned in required-check order: `FRESHNESS`, `COMPLETENESS`, `LINEAGE`, `RECONCILIATION`, `PUBLICATION_READINESS`
- `snapshot_id`, `data_version`, and `service_version` must be non-empty
- `generated_at` must be deterministic for a pinned snapshot context and derived from snapshot metadata or another pinned source

### `ControlCheckResult`

Validation rules:

- `check_type` must be unique within one `IntegrityAssessment`
- `reason_codes` may be empty only when `check_state = PASS`
- `reason_codes` must be deduplicated and deterministically ordered
- `evidence_refs` must contain at least one reference when `check_state` is `WARN` or `FAIL`
- `evidence_refs` may be empty when `check_state = UNKNOWN` only if `reason_codes` includes `CHECK_RESULT_MISSING`

### `EvidenceRef`

Validation rules:

- `evidence_type` and `evidence_id` must be non-empty
- `snapshot_id` must be present when the evidence is snapshot-scoped
- `source_as_of_date` must be on or before `as_of_date`

## Interfaces / APIs

### `get_integrity_assessment`

Purpose:
Return one deterministic trust assessment for a single target in a pinned snapshot context.

Inputs:

- `node_ref`
- `measure_type`
- `as_of_date`
- `snapshot_id=None`

Returns:

- `IntegrityAssessment` when the current target and enough normalized control context exist to populate the object honestly
- typed service error `MISSING_SNAPSHOT` when the pinned or resolved current snapshot cannot be found
- typed service error `MISSING_NODE` when the scoped node cannot be resolved in the pinned dataset context
- typed service error `MISSING_CONTROL_CONTEXT` when no required control records can be resolved for the pinned target and snapshot context
- typed request validation failure for invalid request inputs

Interface rules:

- read-only deterministic service only
- no free-text search or fuzzy node resolution
- no current-value risk recomputation inside this service
- no hidden fallback from missing control context to `TRUSTED`

## Business rules

1. The service assesses trust for a target already identified by canonical scope and measure.
2. v1 trust logic uses only normalized control check records; raw operational-source interpretation is out of scope.
3. Every assessment must evaluate exactly the five required check types.
4. Trust-state precedence is:
   - any `FAIL` on a required check -> `BLOCKED`
   - otherwise any `UNKNOWN` on a required check -> `UNRESOLVED`
   - otherwise any `WARN` on a required check -> `CAUTION`
   - otherwise `TRUSTED`
5. False-signal-risk mapping is:
   - `BLOCKED` -> `HIGH`
   - `CAUTION` -> `MEDIUM`
   - `UNRESOLVED` -> `UNKNOWN`
   - `TRUSTED` -> `LOW`
6. `assessment_status = OK` only when all required check results are resolved in the pinned control context and every non-pass result carries required evidence references.
7. `assessment_status = DEGRADED` when the object is still returnable but any required check is `UNKNOWN`, any normalized control row is degraded, or any required evidence reference is missing.
8. `blocking_reason_codes` must be the deduplicated deterministic union of reason codes from all `FAIL` check results, preserving the required-check order traversal.
9. `cautionary_reason_codes` must be the deduplicated deterministic union of reason codes from all `WARN` and `UNKNOWN` check results, preserving the required-check order traversal.
10. This service does not determine market causality, remediation priority, or governance closure.

## Trust-state and assessment-status interaction

These fields answer different questions and must not be collapsed together.

| Scenario | trust_state | assessment_status | Required interpretation |
|---|---|---|---|
| all required checks pass | `TRUSTED` | `OK` | safe to interpret as operationally clean |
| one or more required checks warn, evidence complete, no degraded row | `CAUTION` | `OK` | interpretable with caveats |
| one or more required checks fail, evidence complete, no degraded row | `BLOCKED` | `OK` | blocked because controls indicate the signal is not trustworthy enough |
| one or more required checks are unknown | `UNRESOLVED` | `DEGRADED` | returnable object, but trust cannot be resolved honestly |
| one or more required checks fail and required evidence is missing | `BLOCKED` | `DEGRADED` | controls still block interpretation, and the returned object is itself degraded |
| no control-context object can be formed at all | no object | no object | return typed service error, not an `IntegrityAssessment` |

## State model

This is a stateless read-only retrieval service.

There is no workflow state in scope. The only stateful context is the pinned snapshot and normalized control records retrieved for that request.

## Error handling and degraded cases

### Canonical service-error vocabulary

This PRD reuses the shared Phase 1 service-error envelope pattern.

For this service, the governed non-object error statuses are:

- `MISSING_SNAPSHOT`
- `MISSING_NODE`
- `MISSING_CONTROL_CONTEXT`

Returned-object `assessment_status` values remain `OK` and `DEGRADED` only.

### Case: invalid request

Result:

- typed request validation failure
- no `IntegrityAssessment` returned
- examples include blank `snapshot_id`, snapshot/date mismatch, or invalid `node_ref` scope semantics

### Case: current snapshot missing

Result:

- typed service error `MISSING_SNAPSHOT`
- no fabricated assessment object

### Case: target missing in pinned context

Result:

- typed service error `MISSING_NODE`
- no fabricated assessment object

This preserves the Phase 1 rule that the service must not claim a trustworthy target when the target itself cannot be resolved honestly.

### Case: all required control context missing

Result:

- typed service error `MISSING_CONTROL_CONTEXT`
- no fabricated assessment object

### Case: partial control context available

Result:

- return `IntegrityAssessment`
- any missing required check becomes `check_state = UNKNOWN`
- `trust_state = UNRESOLVED`
- `assessment_status = DEGRADED`
- include reason code `CHECK_RESULT_MISSING` on each missing check

### Case: degraded normalized control rows

Result:

- return `IntegrityAssessment`
- affected checks retain their normalized check state
- `assessment_status = DEGRADED`
- include explicit degraded reason codes

### Case: warning-only control issues

Result:

- return `IntegrityAssessment`
- `trust_state = CAUTION`
- `false_signal_risk = MEDIUM`
- `assessment_status = OK` when evidence requirements are satisfied and no degraded row exists

### Case: one or more failed required checks

Result:

- return `IntegrityAssessment`
- `trust_state = BLOCKED`
- `false_signal_risk = HIGH`
- `assessment_status = OK` when evidence requirements are satisfied and no degraded row exists

## Evidence, logging, and replay

### Reuse from Phase 1

This PRD reuses the following Phase 1 infrastructure patterns directly:

- typed Pydantic-based contracts from ADR-001
- shared service-error envelope from `src/shared`
- pinned snapshot replay behavior from ADR-002
- deterministic generated-at semantics tied to pinned snapshot context
- typed `NodeRef`, hierarchy-scope, and measure semantics from PRD-1.1

### New work in this PRD

This PRD adds:

- trust-state and control-check enums
- module-level integrity assessment contracts
- normalized control fixture pack aligned to risk snapshots
- deterministic trust-state aggregation rules

### Evidence requirements

- each `WARN` and `FAIL` check result must carry typed `evidence_refs`
- `status_reasons`-style prose substitution is forbidden for evidence
- replay artifacts must pin the resolved request context and the normalized control records used for the decision

### Logging requirements

Minimum structured logging should include:

- request or correlation id
- operation variant
- `node_ref`
- `measure_type`
- `as_of_date`
- `snapshot_id` when provided
- returned `trust_state`
- returned `assessment_status`
- count of failed, warned, and unknown checks
- duration

### Replay requirements

- service must support replay by `snapshot_id`
- same resolved request plus same normalized control records plus same snapshot must yield the same output
- replay-stable output requires deterministic ordering for `check_results`, `reason_codes`, `blocking_reason_codes`, and `cautionary_reason_codes`
- replay output must not depend on wall-clock execution time
- any change to trust-state mapping, required check set, or evidence-field semantics requires a `service_version` bump and replay-fixture refresh

## Security and control constraints

- read-only deterministic service
- no direct mutation of control records
- no hidden policy overrides
- no inferred human sign-off or remediation decision
- no UI-specific formatting or suppression of caveats

## Acceptance criteria

### Functional

- returns `IntegrityAssessment` for a valid target with normalized control records
- returns `TRUSTED`, `CAUTION`, `BLOCKED`, and `UNRESOLVED` correctly according to the governed precedence rules
- returns `MISSING_SNAPSHOT`, `MISSING_NODE`, and `MISSING_CONTROL_CONTEXT` as typed service errors when applicable
- preserves exact target scope semantics from Phase 1

### Data-contract

- all outputs conform to typed schemas
- all five required checks are present exactly once in every returned object
- mirror fields remain consistent with `node_ref`
- evidence references remain typed objects, not prose strings

### Architecture

- trust logic remains in `src/modules/`
- walkers consume the typed assessment rather than inventing canonical trust classification
- orchestrators use trust state for routing but do not own the rules
- UI does not recompute trust-state or hide caveats

### Replay

- same pinned snapshot and normalized control inputs reproduce the same assessment
- degraded and unresolved cases are replay-stable

## Test cases

### Positive

- all five required checks pass and the service returns `TRUSTED`
- one warning check with evidence returns `CAUTION`
- one failed check with evidence returns `BLOCKED`

### Negative

- missing snapshot
- missing node
- missing all control context

### Edge

- one required check missing, producing `UNRESOLVED` and `DEGRADED`
- degraded normalized control row with a warning result
- same logical node in different legal entities returns distinct assessments when control records differ

### Replay

- same pinned snapshot reproduces the same trust outcome
- replay detects service-version change when trust precedence rules change

## Dependencies and sequencing

### Blocking dependencies

- PRD-1.1 risk-summary target identity and snapshot semantics must remain the source of truth
- shared error-envelope pattern in `src/shared` remains unchanged

### Downstream work unblocked by this PRD

- Data Controller Walker PRD implementation
- Daily Risk Investigation trust-gating stage
- governance outputs that need deterministic trust-state input

### Fixture needs

Create a small synthetic control fixture pack aligned to the Phase 1 risk fixture pack with:

- at least 2 legal entities
- at least 3 distinct nodes
- one all-pass case
- one warning case
- one blocking failure case
- one unresolved missing-check case
- one degraded control-row case

## Reuse and gap analysis

### Reuse from completed work

- reuse `NodeRef`, `MeasureType`, and hierarchy-scope semantics from Phase 1
- reuse shared service-error envelope and request-validation boundary pattern
- reuse snapshot pinning and replay conventions
- reuse deterministic fixture and replay-test approach

### New capability work

- new module package under `src/modules/controls_integrity/`
- new contracts for trust-state, check-state, and integrity assessments
- new normalized control fixture index and retrieval logic
- new deterministic rule engine for trust aggregation

### Remaining gaps

- ADR-003 direction exists, but a repo-wide shared typed `EvidenceRef` object is still not implemented
- this PRD is deliberately bounded to module-level evidence objects so coding does not have to invent prose fields or redesign shared contracts
- FRTB / PLA desk-control semantics remain a separate later PRD and must not be folded into this slice

## Issue decomposition guidance

Implementation sequencing should decompose into `WI-2.1.x` items only. Do not reopen `WI-1.1.x`.

Recommended issue families:

- `WI-2.1.1` contracts and enums
  - add typed schemas and enums for trust-state, check-state, evidence refs, and integrity assessments
  - target area: `src/modules/controls_integrity/contracts/`, `src/shared/` only if PM explicitly approves shared evidence-object extraction

- `WI-2.1.2` normalized control fixtures and fixture index
  - build replayable control fixture pack aligned to the Phase 1 snapshot and node identities
  - target area: `src/modules/controls_integrity/fixtures/`, `fixtures/`, `tests/replay/`

- `WI-2.1.3` deterministic service implementation
  - implement `get_integrity_assessment` and rule precedence exactly as specified here
  - target area: `src/modules/controls_integrity/service.py`

- `WI-2.1.4` degraded, negative, and replay validation
  - add unit and replay coverage for missing, unresolved, degraded, and scope-differentiated cases
  - target area: `tests/unit/`, `tests/replay/`

Sequencing constraints:

- contracts first
- fixtures before service logic finalization
- service before walker consumption
- do not start Data Controller Walker implementation until this deterministic service is stable

## Reviewer checklist

- verify the PRD keeps trust logic inside a deterministic module
- verify Phase 1 target and snapshot semantics are reused rather than redefined
- verify degraded and unresolved cases are explicit and reviewable
- verify evidence references remain typed and non-prose
- verify FRTB / PLA semantics have not leaked into this PRD

## AI agent instructions

### Coding agent

- implement only the deterministic controls-integrity service slice
- do not move trust logic into walkers or orchestrators
- do not redesign `NodeRef`, `MeasureType`, or the shared service-error envelope

### Review agent

- review for contract fidelity, status precedence, replayability, and boundary discipline
- flag any attempt to infer trust from raw external data feeds inside this first slice

### PM agent

- split only into `WI-2.1.x` items
- keep FRTB / PLA controls as a later separate PRD or sub-phase item

## Open questions

- **ADR / shared-contract gap:** ADR-003 establishes the need for structured evidence references, but the repository does not yet have a repo-wide shared `EvidenceRef` object in `src/shared/`. This PRD is still implementable with a module-local nested `EvidenceRef`, but PM should decide whether `WI-2.1.1` includes a narrow shared-object extraction.
- **No further blocking methodology question:** This slice intentionally avoids FRTB / PLA methodology so no additional regulatory-methodology ADR is required for PRD-2.1 itself.
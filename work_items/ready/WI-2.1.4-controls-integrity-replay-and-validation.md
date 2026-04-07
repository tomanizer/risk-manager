# WI-2.1.4

## Linked PRD

PRD-2.1

## Linked ADRs

- ADR-002
- ADR-003

## Purpose

Add replay and regression coverage that proves the controls-integrity service is stable enough for downstream walker consumption without reopening service semantics.

## Scope

- add replay coverage for pinned `snapshot_id` re-execution of `get_integrity_assessment`
- add replay assertions for stable `trust_state`, `assessment_status`, `check_results`, reason-code ordering, `generated_at`, `data_version`, and `service_version`
- add regression coverage for degraded rows, missing evidence, missing required checks, and distinct legal-entity outcomes
- prove replay stability for positive, negative, and degraded returned-object cases
- keep this slice limited to tests and replay artifacts needed to validate the completed deterministic service

## Out of scope

- new service logic beyond bug fixes strictly required by tests
- Data Controller Walker implementation
- orchestrator trust-gating implementation
- UI work
- schema redesign
- FRTB / PLA controls

## Dependencies

- WI-2.1.3-integrity-assessment-service
- ADR-002-replay-and-snapshot-model
- ADR-003-evidence-and-trace-model

## Target Area

- `tests/replay/controls_integrity/`
- `tests/unit/modules/controls_integrity/`
- `fixtures/controls_integrity/` only for replay fixtures already required by the completed service

## Acceptance Criteria

- replay tests prove that the same resolved request plus the same pinned snapshot and normalized control records produce the same `IntegrityAssessment`
- replay assertions cover `snapshot_id`, `data_version`, `service_version`, `generated_at`, trust-state, assessment-status, required-check ordering, and reason-code ordering
- degraded and unresolved returned-object cases are replay-stable
- replay coverage includes one `TRUSTED`, one `CAUTION`, one `BLOCKED`, and one `UNRESOLVED` case
- regression coverage includes missing evidence, degraded rows, missing required checks, and differing outcomes for different legal entities when control context differs
- this slice does not add walker, orchestrator, or UI logic

## Test Intent

- replay tests for stable deterministic output under repeated execution
- regression tests for degraded-case semantics and evidence propagation
- regression tests for cross-entity differentiation and ordering guarantees

## Why This Unblocks Downstream Work

This gives later walker and orchestrator slices a verified replay-safe deterministic trust input, so they can consume the service without reopening trust logic, degraded behavior, or evidence propagation.

## Residual Blocker / Escalation

None.

## Suggested Agent

Coding Agent

## Review Focus

- replay determinism
- degraded-case coverage completeness
- evidence propagation in replay outputs
- strict scope discipline around downstream consumer work
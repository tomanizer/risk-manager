# WI-2.1.1

## Linked PRD

PRD-2.1

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Purpose

Define the canonical typed contract surface for the Controls and Production Integrity Assessment Service so fixtures, service logic, and downstream consumers share one deterministic schema.

## Scope

- create `src/modules/controls_integrity/contracts/`
- add enums for required check types, check states, trust states, and false-signal risk
- add typed models for normalized control records, `EvidenceRef`, `ControlCheckResult`, and `IntegrityAssessment`
- enforce exact required-check ordering
- enforce reason-code deduplication and lexicographic ordering
- enforce mirror-field fidelity from `node_ref`
- preserve replay and version metadata requirements from PRD-2.1
- keep request-validation and typed non-object error handling aligned with the existing shared service-error envelope pattern

## Out of scope

- fixture pack creation
- fixture indexing or loader implementation
- `get_integrity_assessment` service logic
- walker or orchestrator consumption
- UI work
- FRTB / PLA controls
- repo-wide evidence-contract redesign beyond the narrow `EvidenceRef` placement decision

## Dependencies

- PRD-2.1-controls-production-integrity-assessment-service
- ADR-001-schema-and-typing-approach
- ADR-002-replay-and-snapshot-model
- ADR-003-evidence-and-trace-model
- ADR-004-business-day-and-calendar-handling
- WI-1.1.1-risk-summary-schemas
- WI-1.1.9-shared-service-error-envelope

## Target Area

- `src/modules/controls_integrity/contracts/`
- `src/modules/controls_integrity/__init__.py`
- `tests/unit/modules/controls_integrity/`
- `src/shared/` only if PM explicitly approves a narrow shared `EvidenceRef` extraction in this slice

## Acceptance Criteria

- all PRD-2.1 enums and typed models exist explicitly and validate deterministically
- `IntegrityAssessment` requires exactly one result for each required check in this order: `FRESHNESS`, `COMPLETENESS`, `LINEAGE`, `RECONCILIATION`, `PUBLICATION_READINESS`
- top-level `node_level`, `hierarchy_scope`, and `legal_entity_id` fields mirror `node_ref` exactly
- `blocking_reason_codes` and `cautionary_reason_codes` are deduplicated and lexicographically ordered ascending
- per-check `reason_codes` are deduplicated and lexicographically ordered ascending
- `WARN` and `FAIL` check results require typed `evidence_refs`
- `UNKNOWN` check results may have empty `evidence_refs` only when `reason_codes` includes `CHECK_RESULT_MISSING`
- `snapshot_id`, `data_version`, and `service_version` are required non-empty fields on `IntegrityAssessment`
- this slice does not invent a service-specific error envelope or prose-only evidence fields

## Test Intent

- unit tests for enum values and schema validation
- unit tests for mirror-field enforcement from `node_ref`
- unit tests for exact required-check ordering and uniqueness
- unit tests for reason-code ordering and deduplication
- unit tests for evidence-reference validation rules across `PASS`, `WARN`, `FAIL`, and `UNKNOWN`
- unit tests for rejection of invalid or partial contract shapes

## Why This Unblocks Downstream Work

This creates the governed contract layer needed before fixture packs, service logic, and later walker consumption can proceed without inventing trust or evidence semantics.

## Residual Blocker / Escalation

PM or human decision required only on the narrow open question from PRD-2.1: whether `EvidenceRef` remains module-local in this slice or is extracted narrowly into `src/shared/`. The narrower default is to keep it module-local.

## Suggested Agent

Coding Agent

## Review Focus

- contract fidelity to PRD-2.1
- explicit degraded and evidence semantics
- replay metadata completeness
- no architecture widening beyond the approved contract layer
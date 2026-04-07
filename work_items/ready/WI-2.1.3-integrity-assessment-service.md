# WI-2.1.3

## Linked PRD

PRD-2.1

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Purpose

Implement `get_integrity_assessment` as the canonical deterministic trust-assessment service for one target in one pinned snapshot context.

## Scope

- create `src/modules/controls_integrity/service.py`
- resolve the pinned or canonical snapshot for the request
- validate `snapshot_id` and `as_of_date` consistency
- verify target existence in the pinned context using Phase 1 target semantics
- retrieve normalized control rows from the controls-integrity fixture index
- implement exact trust-state precedence from PRD-2.1
- implement exact false-signal-risk mapping from PRD-2.1
- implement exact `assessment_status` rules for `OK` and `DEGRADED`
- implement missing-check, degraded-row, and missing-evidence handling
- implement deduplicated and lexicographically ordered blocking and cautionary reason-code unions
- preserve deterministic `generated_at`, `snapshot_id`, `data_version`, and `service_version` behavior
- export the service from the module package

## Out of scope

- raw-source control normalization
- calendar-policy implementation inside the service
- Data Controller Walker logic
- orchestrator routing logic
- UI rendering
- batch ranking across many nodes
- FRTB / PLA controls
- contract redesign outside the named service surface

## Dependencies

- WI-2.1.1-controls-integrity-contracts-and-enums
- WI-2.1.2-controls-integrity-fixtures-and-index
- WI-1.1.9-shared-service-error-envelope
- ADR-001-schema-and-typing-approach
- ADR-002-replay-and-snapshot-model
- ADR-003-evidence-and-trace-model
- ADR-004-business-day-and-calendar-handling

## Target Area

- `src/modules/controls_integrity/service.py`
- `src/modules/controls_integrity/__init__.py`
- `tests/unit/modules/controls_integrity/`
- `src/shared/service_errors.py` only for reuse of the existing typed error-envelope pattern, not for semantic redesign

## Acceptance Criteria

- `get_integrity_assessment` returns an `IntegrityAssessment` only when the request can be populated honestly from pinned control context
- typed service errors are returned for `MISSING_SNAPSHOT`, `MISSING_NODE`, and `MISSING_CONTROL_CONTEXT`
- invalid request inputs fail through typed validation rather than hidden fallback behavior
- every returned `IntegrityAssessment` contains exactly the five required checks in governed order
- trust-state precedence is exactly: any `FAIL` -> `BLOCKED`, else any `UNKNOWN` -> `UNRESOLVED`, else any `WARN` -> `CAUTION`, else `TRUSTED`
- false-signal-risk mapping is exactly: `BLOCKED` -> `HIGH`, `CAUTION` -> `MEDIUM`, `UNRESOLVED` -> `UNKNOWN`, `TRUSTED` -> `LOW`
- missing required checks become `UNKNOWN` with `CHECK_RESULT_MISSING`, `trust_state = UNRESOLVED`, and `assessment_status = DEGRADED`
- degraded rows preserve their normalized check state and add `CONTROL_ROW_DEGRADED`
- missing required evidence references add `EVIDENCE_REF_MISSING` and degrade the returned object
- `blocking_reason_codes` and `cautionary_reason_codes` are deduplicated and lexicographically ordered ascending
- no hidden fallback from a pinned `snapshot_id` to latest-available behavior is introduced

## Test Intent

- unit tests for `TRUSTED`, `CAUTION`, `BLOCKED`, and `UNRESOLVED` outcomes
- unit tests for `MISSING_SNAPSHOT`, `MISSING_NODE`, and `MISSING_CONTROL_CONTEXT`
- unit tests for snapshot-date mismatch validation
- unit tests for missing-check handling and degraded-row handling
- unit tests for missing-evidence degradation
- unit tests for ordered reason-code aggregation and stable check-result ordering

## Why This Unblocks Downstream Work

This produces the single canonical trust answer that the Data Controller Walker and daily-investigation trust gate need, while keeping trust logic inside the deterministic module boundary.

## Residual Blocker / Escalation

None. This WI proceeds with module-local `EvidenceRef` handling inside `src/modules/controls_integrity/service.py`, assuming WI-2.1.2 delivers the normalized-control fixture contract unchanged.

Any later extraction of shared `EvidenceRef` handling is out of scope for this WI and must be proposed as a separate, explicitly gated follow-up.

## Suggested Agent

Coding Agent

## Review Focus

- exact trust and degraded-case semantics
- object-versus-service-error boundary discipline
- replay-safe pinned snapshot behavior
- no leakage of trust logic into later-layer components
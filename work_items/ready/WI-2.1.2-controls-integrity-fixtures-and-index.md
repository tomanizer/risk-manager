# WI-2.1.2

## Linked PRD

PRD-2.1

## Linked ADRs

- ADR-002
- ADR-004

## Purpose

Create the deterministic normalized-control fixture pack and fixture index that the service will use in pinned snapshot context.

## Scope

- create a synthetic controls-integrity fixture pack aligned to the Phase 1 node identity and snapshot model
- create a fixture schema for normalized control rows and snapshot metadata
- create `src/modules/controls_integrity/fixtures/` loader and index helpers
- support lookup by `node_ref`, `measure_type`, `as_of_date`, resolved `snapshot_id`, and `check_type`
- encode the required uniqueness boundary of one normalized control row per target, snapshot, and check type
- pin the calendar basis used upstream for `FRESHNESS` and `PUBLICATION_READINESS` normalization
- include typed evidence references and row degradation flags in fixture records

## Out of scope

- trust-state aggregation logic
- `get_integrity_assessment` implementation
- raw operational-feed normalization
- duplicate-row winner selection or deduplication policy
- walker or orchestrator work
- UI work
- FRTB / PLA controls

## Dependencies

- WI-2.1.1-controls-integrity-contracts-and-enums
- ADR-002-replay-and-snapshot-model
- ADR-004-business-day-and-calendar-handling
- WI-1.1.2-risk-summary-fixtures

## Target Area

- `fixtures/controls_integrity/`
- `src/modules/controls_integrity/fixtures/`
- `src/modules/controls_integrity/__init__.py`
- `tests/unit/modules/controls_integrity/`

## Acceptance Criteria

- fixture pack includes at least 2 legal entities and at least 3 distinct nodes aligned to Phase 1 target identity conventions
- fixture pack includes one all-pass case, one warning case, one blocking failure case, one unresolved missing-check case, and one degraded control-row case
- each normalized control row includes `node_ref`, `measure_type`, `as_of_date`, `snapshot_id`, `check_type`, `check_state`, `reason_codes`, `evidence_refs`, and `is_row_degraded`
- loader and index are deterministic and replay-safe
- duplicate uniqueness keys are rejected as invalid fixture data rather than silently deduplicated
- fixture metadata pins `snapshot_id`, `data_version`, `service_version`, and the calendar basis used to normalize freshness-sensitive checks

## Test Intent

- unit tests for fixture loading and schema validation
- unit tests for deterministic indexing by target and check type
- unit tests for duplicate-key rejection
- unit tests for missing-check representation and degraded-row preservation
- unit tests proving distinct legal-entity control context can produce different indexed records for the same logical node

## Why This Unblocks Downstream Work

This provides the replayable control context required before service logic can be implemented honestly and before later consumers can rely on pinned trust outcomes.

## Residual Blocker / Escalation

None if WI-2.1.1 resolves the `EvidenceRef` placement decision. If that decision is deferred, keep `EvidenceRef` module-local in this fixture slice.

## Suggested Agent

Coding Agent

## Review Focus

- replay determinism
- target and snapshot alignment with Phase 1
- duplicate-row handling discipline
- degraded-case coverage in fixtures
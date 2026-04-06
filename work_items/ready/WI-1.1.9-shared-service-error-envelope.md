# WI-1.1.9

## Linked PRD

PRD-1.1-v2

## Purpose

Implement the minimal shared typed service-error path required for as-of-date deterministic service retrieval so `WI-1.1.4` can surface canonical non-object outcomes without inventing a `risk_analytics`-local error envelope or widening `RiskDelta`.

## Scope

- add a minimal shared typed service-error model under `src/shared/`
- add a minimal shared typed request-validation-failure model under `src/shared/`
- make the shared models generic enough to carry:
  - operation variant
  - canonical status code
  - explicit `status_reasons`
- keep the shared models independent of `RiskDelta`, `RiskSummary`, and `RiskChangeProfile`
- expose the shared models through the shared package export surface
- add unit tests for shared-model validation and construction behavior

## Out of scope

- changes to PRD semantics
- changes to `RiskDelta`, `RiskSummary`, or `RiskChangeProfile`
- changes to `src/modules/risk_analytics/service.py`
- changes to `WI-1.1.4` implementation logic
- replay-suite coverage
- new evidence or trace fields beyond the minimal shared error path
- repo-wide exception-framework redesign
- module-specific error envelopes inside `risk_analytics`

## Dependencies

- PRD-1.1-v2
- WI-1.1.1-risk-summary-schemas
- ADR-001
- ADR-002
- ADR-003

## Target Area

- src/shared/service_errors.py
- src/shared/__init__.py
- tests/unit/shared/test_service_errors.py

## Acceptance Criteria

- a shared typed service-error model exists in the target shared service-errors module
- a shared typed request-validation-failure model exists in the target shared service-errors module
- the shared service-error model can represent `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, and `MISSING_NODE` without requiring any `RiskDelta` fields such as:
  - `current_value`
  - `snapshot_id`
  - `data_version`
  - `service_version`
  - `generated_at`
- the shared models require an explicit canonical status code and support explicit `status_reasons`
- the shared models support an explicit operation identifier so `WI-1.1.4` can use them for `get_risk_delta` without introducing a delta-local contract
- the shared models are importable from the shared package export surface
- the shared models do not encode `risk_analytics`-specific payload fields
- unit tests validate required fields, non-empty status codes, and explicit separation between service-error outcomes and request-validation-failure outcomes
- this slice does not modify `RiskDelta` or any `risk_analytics` object contract

## Test Intent

- unit tests for constructing a shared service error with canonical status codes
- unit tests for constructing a shared request-validation failure
- validation tests for missing or blank required fields
- tests proving the shared models do not require `RiskDelta` payload fields
- tests proving `status_reasons` remain explicit and typed
- tests proving the shared models are importable from `src/shared`

## Suggested Agent

Coding Agent

## Review Focus

- shared-versus-local boundary discipline
- no hidden `risk_analytics` coupling in the shared models
- contract minimality
- readiness for `WI-1.1.4` reuse without schema widening

## Why This Unblocks WI-1.1.4

`WI-1.1.4` already has canon for which delta outcomes are typed objects versus typed service errors, but current `origin/main` does not expose a concrete shared implementation path for those non-object outcomes. This slice provides that shared path in `src/shared/`, so `WI-1.1.4` can surface `UNSUPPORTED_MEASURE`, `MISSING_SNAPSHOT`, and `MISSING_NODE` as typed service errors without inventing a delta-local envelope or widening `RiskDelta`.

## Residual Blocker

None, if this slice is accepted as the repository's minimal shared typed service-error path. The remaining gap is implementation scaffolding, not PRD or architecture semantics.

# Shared Infrastructure Canon

## Purpose

This canon defines repository-wide infrastructure components that are shared
across modules, walkers, orchestrators, and agent-runtime integrations.

It exists to prevent local reinvention and to keep contracts stable for PM,
PRD/spec, issue-planning, coding, and review workflows.

## Scope

Shared infrastructure includes:

- telemetry (structured logs, trace context, metrics hooks)
- shared error/status semantics
- replay/evidence helper surfaces
- cross-cutting utility contracts that multiple bounded slices depend on

## Source-of-truth rule

- Shared infrastructure behavior must be specified in `docs/shared_infra/`.
- Reusable implementation belongs in `src/shared/`.
- Module-local wrappers are allowed only when they are thin pass-throughs that
  do not extend or modify shared contracts.

## Ownership and change control

- Cross-cutting infra behavior changes require explicit PM visibility.
- If change semantics are architectural or contract-breaking, link an ADR.
- Work items touching shared infra must declare:
  - impacted components
  - migration/adoption impact
  - backward-compatibility expectations

## Required references by role

- PM agent: validate shared-infra dependency readiness before assigning coding.
- PRD/spec author: define shared-infra contract expectations explicitly.
- Issue planner: sequence shared-infra prerequisite slices before dependents.
- Coding agent: reuse `src/shared/` primitives; avoid local reinvention.
- Review agent: check contract drift and duplicate-framework creation.

## Documents in this canon

- `docs/shared_infra/telemetry.md`
- `docs/shared_infra/adoption_matrix.md`


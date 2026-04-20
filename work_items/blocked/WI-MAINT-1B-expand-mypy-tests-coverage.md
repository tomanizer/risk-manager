# WI-MAINT-1B

## Status

**BLOCKED / POLICY-GATED** — not coding-ready. Current `main` facts are intentionally preserved here rather than delegated to coding: CI enforces `mypy src/ agent_runtime/`, while `python -m mypy src/ tests/` fails with many existing errors.

## Blocker

- Explicit PM / human approval is required to change policy and expand the mypy-enforced path set to include `tests/`.
- The exact expanded path set must be stated explicitly before coding begins.

## Linked PRD

None — repository tooling maintenance with a policy decision. This item exists only if the repository intends to widen mypy enforcement beyond current CI.

## Linked ADRs

None required.

## Linked shared infra

None.

## Purpose

Expand mypy coverage to `tests/` only if policy intent is to widen enforcement beyond the current CI path set.

## Scope

- State the exact expanded mypy path set explicitly, with `tests/` included only if approved
- Align CI and pre-commit to the same approved expanded path set
- Perform only the typing cleanup required in `tests/` for the approved invocation to pass cleanly

## Out of scope

- Architecture changes
- Unrelated production-code changes
- Asking coding to decide whether policy should change

## Dependencies

- Explicit PM / human approval to expand mypy coverage to `tests/`

## Target area

- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
- `tests/` only, for typing cleanup required by the approved expansion

## Acceptance criteria

### Policy

- The exact expanded path set is stated explicitly in the work item before coding starts

### Configuration

- CI and pre-commit use the same expanded path set

### Verification

- The expanded invocation passes cleanly

## Stop conditions

- Stop if PM / human approval to expand coverage is absent
- Stop if coding would need to choose the policy intent or choose the expanded path set
- Stop if clean verification requires architecture changes or unrelated production-code changes

## Review focus

- Policy approval is attached and unambiguous
- The expanded path set is identical in CI and pre-commit
- Any typing cleanup is confined to `tests/` and is only what is required for the approved path expansion

## Suggested agent

PM / human decision first; Coding Agent only after the blocker is cleared

# WI-MAINT-1B

## Status

**ARCHIVED / POLICY REJECTED** — on 2026-04-20, PM / human decision fixed repository mypy enforcement to `src/` and `agent_runtime/` only. Expanding enforcement to `tests/` is not approved and is not a coding-ready slice.

## Blocker

- None. This archived note records a closed policy decision rather than an active coding blocker.

## Linked PRD

None — repository tooling maintenance. No PRD is required because the decision is to preserve the current enforcement boundary rather than widen it.

## Linked ADRs

None required.

## Linked shared infra

None.

## Decision outcome

- CI enforcement remains `mypy src/ agent_runtime/`.
- Pre-commit enforcement remains `mypy src/ agent_runtime/`.
- Mypy enforcement does **not** expand to `tests/`.
- No coding work should be assigned from this item.

## Reason for rejection

- The approved maintenance outcome was CI / pre-commit parity for the current path set, completed by `WI-MAINT-1A`.
- Expanding into `tests/` would be a governance policy change, not a routine coding follow-on.
- Current repository facts do not support a narrow follow-up: `python -m mypy src/ tests/` fails broadly across many test files, so this is not a bounded config-only change.

## Correct backlog state

- Keep [`WI-MAINT-1A-mypy-pre-commit-hook-ci-parity.md`](../done/WI-MAINT-1A-mypy-pre-commit-hook-ci-parity.md) in `work_items/done/`.
- Keep this `WI-MAINT-1B` note in `work_items/archived/` as a recorded rejected path.
- Do not recreate a `blocked/` or `ready/` item for test-coverage expansion unless a future human policy decision changes.

## Out of scope

- Any CI change that widens mypy beyond `src/` and `agent_runtime/`
- Any typing cleanup in `tests/`
- Asking coding to revisit this decision without a new explicit human policy change

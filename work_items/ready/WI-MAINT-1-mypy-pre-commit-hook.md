# WI-MAINT-1

## Status

**READY** — gap confirmed by drift-monitor 2026-04-19; no architecture decision required; `.pre-commit-config.yaml` target is concrete.

## Linked PRD

None — repository tooling maintenance. Policy basis: mypy type-checking is a CI enforcement requirement. This WI closes the local-gate gap so pre-commit mirrors CI enforcement.

## Linked ADRs

None required.

## Linked shared infra

None.

## Purpose

Add a mypy pre-commit hook so type-checking runs locally before every commit, not only in CI. This eliminates the conditions that caused PR #175 to use `--no-verify` and ensures local and CI enforcement are consistent.

## Background

Drift-monitor pass (2026-04-19, WATCH status) identified that `.pre-commit-config.yaml` contains only `ruff-format` and `ruff` hooks. CI runs mypy, but there is no local pre-commit gate. This gap allowed `--no-verify` to bypass type checking silently. The fix is bounded and has no architectural implications.

## Scope

- Add a `mypy` hook to `.pre-commit-config.yaml` covering:
  - `src/`
  - `tests/`
- Hook must use the project's installed mypy (not a standalone mirror) to respect `pyproject.toml` configuration.
- Verify that the hook runs cleanly on current `main` (zero errors expected, since CI already passes mypy).

## Out of scope

- Changes to mypy configuration in `pyproject.toml`
- Adding new type annotations to pass mypy (if mypy already passes CI, it passes pre-commit; any annotation gaps are a separate item)
- CI workflow changes
- Any `src/` or `tests/` implementation changes

## Target area

- `.pre-commit-config.yaml` (hook addition only)

## Acceptance criteria

### Functional

- `pre-commit run mypy --all-files` exits 0 on current `main`
- `git commit` triggers mypy via pre-commit without requiring `--no-verify`

### Configuration

- Hook is pinned to a specific `mypy` version or uses `repo: local` with `language: system` to match the project's installed version
- Hook passes `args` or `additional_dependencies` consistent with `pyproject.toml` mypy settings

### Test

- No new unit tests required; the acceptance test is a clean `pre-commit run mypy --all-files` run (manual verification by the coding agent, noted in the PR description)

## Dependencies

- None. Unblocked.

## Evidence / replay

Not applicable — tooling configuration only.

## Review focus

- Hook configuration matches CI mypy invocation (same source paths, same config)
- No `--no-verify` usage introduced
- No mypy configuration changed in `pyproject.toml`

## Suggested agent

Coding Agent

## READY_CRITERIA checklist

1. **Linked contract** — Tooling maintenance; no PRD required. Policy basis stated above.
2. **Scope clarity** — Single file change to `.pre-commit-config.yaml`; in/out-of-scope explicit.
3. **Dependency clarity** — No upstream dependencies.
4. **Target location** — `.pre-commit-config.yaml` only.
5. **Acceptance clarity** — Clean `pre-commit run mypy --all-files` exit 0.
6. **Test clarity** — Manual verification; no unit tests required for a config-only change.
7. **Evidence / replay** — Not applicable.
8. **Decision closure** — No unresolved architecture decision.
9. **Shared infra** — Not a shared-infra change.

## Baseline entry (if deferred)

If this WI is deferred, a dated baseline entry should be added to the repo's drift-monitor baseline noting: *mypy pre-commit hook absent — CI-only enforcement — accepted gap as of 2026-04-19 — tracked in WI-MAINT-1*.

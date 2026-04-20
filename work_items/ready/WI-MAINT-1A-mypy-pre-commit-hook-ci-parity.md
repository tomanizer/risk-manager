# WI-MAINT-1A

## Status

**READY** — split approved on 2026-04-20. Current `main` facts are coherent for a config-only slice: CI runs `mypy src/ agent_runtime/`, `.pre-commit-config.yaml` has no mypy hook, and `python -m mypy src/ agent_runtime/` exits 0.

## Blocker

- None. This slice is bounded to a single configuration file and does not require a policy change.

## Linked PRD

None — repository tooling maintenance. Policy basis: local pre-commit enforcement should mirror the current CI mypy invocation exactly, without widening the checked path set.

## Linked ADRs

None required.

## Linked shared infra

None.

## Purpose

Add a mypy pre-commit hook that mirrors current CI exactly by invoking project-installed mypy against `src/` and `agent_runtime/` only.

## Scope

- Update `.pre-commit-config.yaml` only.
- Add a `repo: local` / `language: system` mypy hook that uses the project's installed mypy.
- Configure the hook to run `mypy src/ agent_runtime/` and nothing broader.

## Out of scope

- `tests/` coverage expansion
- CI workflow changes
- `pyproject.toml` changes
- Any source or test typing cleanup

## Dependencies

- None. The slice is intentionally frozen to current CI policy.

## Target area

- `.pre-commit-config.yaml` only

## Acceptance criteria

### Functional

- `pre-commit run mypy --all-files` exits 0 on current `main`
- The hook mirrors the current CI invocation exactly: `mypy src/ agent_runtime/`
- No file other than `.pre-commit-config.yaml` changes

### Configuration

- The hook is implemented as a local/system mypy hook that uses the project-installed mypy
- The checked path set is exactly `src/` and `agent_runtime/`

### Test

- No unit tests are required; acceptance is a clean manual `pre-commit run mypy --all-files` verification

## Stop conditions

- Stop if any file outside `.pre-commit-config.yaml` must change
- Stop if clean verification requires widening coverage beyond current CI

## Review focus

- Hook configuration matches the CI mypy path set exactly
- The hook uses project-installed mypy rather than a separate mirror environment
- No `tests/` expansion, CI workflow edits, `pyproject.toml` edits, or typing-cleanup edits slipped into the PR

## Suggested agent

Coding Agent

## READY_CRITERIA checklist

1. **Linked contract** — Tooling maintenance only; no PRD required. Policy basis is stated explicitly above.
2. **Scope clarity** — Single config-file change; in-scope and out-of-scope boundaries are explicit.
3. **Dependency clarity** — No upstream dependency or unresolved contract is required.
4. **Target location clarity** — `.pre-commit-config.yaml` only.
5. **Acceptance clarity** — Pass/fail is explicit: exact CI-parity invocation, clean `pre-commit` run, and no other file changes.
6. **Test clarity** — Manual verification is explicit and sufficient for a config-only change.
7. **Evidence and replay clarity** — Not applicable; no deterministic service, walker, orchestrator, or governance behavior changes.
8. **Decision closure** — Policy intent is fixed to current CI parity; coding is not asked to decide whether scope should widen.
9. **Shared infrastructure dependency clarity** — None; no shared-infra behavior or adoption change is introduced.

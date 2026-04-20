# WI-MAINT-1

## Status

**SUPERSEDED / ARCHIVED TRANSITION NOTE** — archived on 2026-04-20 because the original ready item mixed a coding-ready CI-parity change with a separate policy decision about expanding mypy coverage to `tests/`.

## Reason for supersession

- Current CI enforcement is `mypy src/ agent_runtime/` in [ci.yml](../../.github/workflows/ci.yml).
- `.pre-commit-config.yaml` currently has no mypy hook, so the immediate gap is CI-parity-only.
- `python -m mypy src/ agent_runtime/` passes on current `main`.
- `python -m mypy src/ tests/` fails with existing errors on current `main`.
- Leaving the original item in `work_items/ready/` would keep a contradictory backlog item that is not assignable under [READY_CRITERIA.md](../READY_CRITERIA.md).

## Canonical replacement items

- [WI-MAINT-1A-mypy-pre-commit-hook-ci-parity.md](../done/WI-MAINT-1A-mypy-pre-commit-hook-ci-parity.md) — completed config-only slice that adds a local/system mypy hook mirroring current CI exactly.
- [WI-MAINT-1B-expand-mypy-tests-coverage.md](../blocked/WI-MAINT-1B-expand-mypy-tests-coverage.md) — blocked follow-on for any policy-approved expansion to `tests/`.

## PM action

- Reassess `WI-MAINT-1A` immediately for coding assignment.
- Keep `WI-MAINT-1B` blocked until PM / human explicitly approves expanding the mypy path set to include `tests/`.

# GitHub Issue Draft

## Suggested Title

Wave 1: fix runtime-managed checkout semantics for PR-follow-up coding

## Suggested Labels

- `agent-runtime`
- `delivery-infra`
- `wave-1`
- `foundation`

## Parent

- Umbrella: [#195](https://github.com/tomanizer/risk-manager/issues/195)
- Linked audit: `docs/guides/agent_runtime_audit_2026-04-21.md`
- Opened as: [#197](https://github.com/tomanizer/risk-manager/issues/197)

## Body

## Problem

For work items with an existing PR, the runtime currently derives a `base_ref` from the PR head branch, but still creates a fresh coding branch for the run. That breaks PR-follow-up semantics.

The result is that runtime-managed coding can open a clean new branch for a fresh slice, but it cannot cleanly continue work on an existing PR without branch divergence and manual recovery.

## Why This Belongs In Wave 1

This is a hard correctness issue for semi-manual and autonomous execution. The runtime cannot be trusted to repair an active PR if it is not operating on the authoritative PR branch.

## Scope

- define explicit runtime checkout modes:
  - fresh slice from current `main`
  - follow-up work on an existing PR head branch
- update worktree allocation so PR-follow-up coding uses the correct authoritative branch model
- persist checkout mode and branch intent in run metadata
- add tests covering:
  - fresh coding branch allocation
  - PR-follow-up coding against an existing branch
  - review worktree semantics

## Out Of Scope

- PR publication policy
- auto-merge
- broader lifecycle side effects

## Dependencies

- none; this is a Wave 1 foundation

## Mode Impact

### Manual

- no direct operator-facing change, but it reduces the chance of runtime advice drifting from the real Git workflow

### Semi-Manual

- runtime-managed coding follow-ups can operate on the same branch as the active PR
- operators no longer need to repair branch topology after a runtime follow-up

### Autonomous

- automated CI-fix and review-follow-up runs can safely continue existing PR work without inventing sibling branches

## Acceptance Criteria

- runtime metadata explicitly distinguishes new-slice and PR-follow-up checkouts
- PR-follow-up coding runs operate on the authoritative PR branch rather than a new branch created from that PR branch
- fresh-slice coding runs still create a clean feature branch from current `main`
- worktree allocation tests cover both cases
- runtime docs no longer imply behavior that the implementation does not provide

## Evidence

- `agent_runtime/orchestrator/execution.py`
- `agent_runtime/orchestrator/worktree_manager.py`
- `agent_runtime/manual_supervisor_workflow.md`
- `agent_runtime/README.md`

## Notes For Work-Item Decomposition

Likely split:

1. checkout-mode design and metadata changes
2. worktree manager implementation changes
3. tests and doc alignment

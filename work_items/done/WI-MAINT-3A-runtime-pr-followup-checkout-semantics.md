# WI-MAINT-3A

## Status

**DONE** - Merged to `main` via [PR #194](https://github.com/tomanizer/risk-manager/pull/194). Runtime-managed checkout semantics now distinguish fresh-slice versus PR-follow-up execution and preserve safe release behavior for non-runtime-owned branches.

## Blocker

- None. Work complete.

## Linked PRD

None - runtime delivery infrastructure maintenance.

Policy basis: [agent_runtime_modernization_plan.md](../../docs/delivery/plans/agent_runtime_modernization_plan.md), [GitHub issue #197](https://github.com/tomanizer/risk-manager/issues/197), [umbrella issue #195](https://github.com/tomanizer/risk-manager/issues/195), and [agent_runtime_audit_2026-04-21.md](../../docs/guides/agent_runtime_audit_2026-04-21.md).

## Linked ADRs

None required.

## Linked shared infra

None.

## Purpose

Make runtime-managed checkout semantics branch-correct by distinguishing fresh-slice runs from PR-follow-up runs and ensuring follow-up coding stays on the authoritative PR head branch instead of creating a sibling feature branch.

## Completion evidence on `main`

- Merge: [PR #194](https://github.com/tomanizer/risk-manager/pull/194)
- `agent_runtime/orchestrator/execution.py` now persists PR-head checkout metadata including `pr_head_branch`, `checkout_ref`, `checkout_detached`, and `branch_owned_by_runtime` for PR-linked coding and review runs.
- `agent_runtime/orchestrator/worktree_manager.py` now allocates detached PR-head worktrees when appropriate and skips branch deletion for non-runtime-owned branches on release.
- `agent_runtime/storage/sqlite.py` now persists `branch_owned_by_runtime` in `worktree_leases`.
- Targeted verification on current `main`: `python -m pytest agent_runtime/tests/test_worktree_manager.py agent_runtime/tests/test_transitions.py -q` -> `50 passed`

## Scope

- Define explicit runtime checkout modes for at least:
  - fresh slice from current `main`
  - coding follow-up on an existing PR head branch
  - review checkout on an existing PR branch
- Update `agent_runtime/orchestrator/execution.py` to persist checkout mode and branch intent in execution metadata.
- Update `agent_runtime/orchestrator/worktree_manager.py` to allocate the correct branch/worktree shape for each checkout mode.
- Persist enough lease metadata to distinguish runtime-created ephemeral branches from attached follow-up branches so release behavior is safe and explicit.
- Update tests covering fresh-slice allocation, PR-follow-up allocation, review checkout semantics, and release behavior.
- Align `agent_runtime/README.md` and `agent_runtime/manual_supervisor_workflow.md` with the implemented checkout policy.

## Out of scope

- PR publication policy redesign
- Auto-merge or auto-promote behavior
- Review comment ingestion or CI log ingestion
- Shared handoff-bundle migration

## Dependencies

- None. This is a Wave 1 correctness foundation for issue `#197`.

## Target area

- `agent_runtime/orchestrator/execution.py`
- `agent_runtime/orchestrator/worktree_manager.py`
- `agent_runtime/storage/sqlite.py`
- `agent_runtime/tests/test_worktree_manager.py`
- `agent_runtime/tests/test_transitions.py`
- `agent_runtime/tests/test_pr_publication.py` only if metadata or branch semantics require coverage updates
- `agent_runtime/README.md`
- `agent_runtime/manual_supervisor_workflow.md`

## Acceptance criteria

- Runtime metadata explicitly distinguishes fresh-slice and PR-follow-up checkouts, and review checkout behavior remains explicit rather than implicit.
- Coding follow-up runs on existing PRs allocate a worktree on the authoritative PR branch instead of inventing a new sibling branch name.
- Fresh-slice coding runs still create a clean runtime-managed feature branch from current `main`.
- Lease metadata records enough branch-ownership intent that release logic does not blindly treat every branch as a disposable runtime-created branch.
- Tests cover fresh allocation, PR-follow-up allocation, review checkout behavior, and safe release behavior.
- Runtime documentation no longer implies checkout behavior that the implementation does not provide.

## Test intent

- Extend worktree-manager tests to cover fresh-slice and PR-follow-up branch allocation separately.
- Extend transition tests to assert checkout-mode metadata and branch intent for coding and review runs.
- Update PR-publication tests only if the new metadata changes how follow-up runs are compared or published.

## Stop conditions

- Stop if the fix requires a broader redesign of PR publication or merge policy.
- Stop if safe release behavior cannot be closed without a new policy decision about local branch retention.
- Stop if the slice expands into post-merge hooks, lifecycle mutation, or other Wave 2 concerns.

## Review focus

- Correctness of checkout-mode and branch-intent semantics
- Preservation of fresh-slice behavior while fixing PR-follow-up behavior
- Safe release behavior for attached PR branches versus runtime-created branches

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

1. **Linked contract** - No PRD is required; the governing contract is the modernization plan, issue `#197`, and the linked audit.
2. **Scope clarity** - The slice is limited to checkout-mode semantics, lease metadata, tests, and doc alignment.
3. **Dependency clarity** - No upstream code dependency must land first.
4. **Target location** - The runtime execution, worktree, storage, test, and doc surfaces are explicit.
5. **Acceptance clarity** - The branch-correct behavior for fresh and follow-up runs is concrete and reviewable.
6. **Test clarity** - Worktree-manager and transition coverage expectations are explicit.
7. **Evidence / replay** - Lease metadata and docs make checkout behavior auditable without widening into full run-artifact work.
8. **Decision closure** - The slice fixes a concrete correctness gap rather than inventing new autonomy policy.
9. **Shared infra** - No shared-infra canon change is required for this runtime checkout fix.

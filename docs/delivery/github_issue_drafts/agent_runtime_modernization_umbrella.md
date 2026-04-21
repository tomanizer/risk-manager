# GitHub Issue Draft

## Suggested Title

Agent Runtime Modernization: unify handoffs, runtime-managed execution, and the path to governed autonomy

## Suggested Labels

- `agent-runtime`
- `delivery-infra`
- `planning`
- `umbrella`

## Parent / Initiative

- Initiative: `agent-runtime-modernization`
- Linked audit: [agent_runtime_audit_2026-04-21.md](../../guides/agent_runtime_audit_2026-04-21.md)
- Linked repo-local plan: [agent_runtime_modernization_plan.md](../plans/agent_runtime_modernization_plan.md)
- Opened as: [#195](https://github.com/tomanizer/risk-manager/issues/195)

## Body

## Summary

The repository currently has three partially overlapping delivery control planes:

1. manual prompt-driven delivery via repo skills and `scripts/invoke.py`
2. semi-autonomous supervision via `agent_runtime`
3. an aspirational autonomous path via opt-in backends, LangGraph, parallel dispatch, post-merge hooks, and autonomy flags

Manual invocation currently works best because it has the richest context and the clearest governance boundaries. The runtime path owns state and worktrees, but it does not yet own the full handoff contract. The automated path is not yet a real end-to-end operating mode.

This issue tracks the modernization work needed to make those paths converge onto one authoritative runtime model.

## Planning Rule

This initiative should be planned by shared capability, not by `manual`, `semi-manual`, and `autonomous` as separate workstreams.

Those three modes remain acceptance lenses on each capability:

- manual
- semi-manual
- autonomous

## Goals

- unify prompt/context generation across manual and runtime flows
- make runtime-managed checkout semantics correct for both fresh slices and PR-follow-up coding
- ensure automated backends use governed role instructions
- make runtime execution durable, replayable, and inspectable
- improve the operator experience without weakening governance boundaries
- create a credible path to governed autonomous execution

## Non-Goals

- replacing repo governance with a single unconstrained coding agent
- enabling auto-merge before the runtime can ingest review and CI context properly
- adding more orchestration framework before the handoff and state model are corrected

## Proposed Wave Structure

## Wave 1 - Foundations

- shared handoff bundle and prompt/context unification
- PR-follow-up checkout semantics for runtime-managed runs
- governed role instructions for automated backends
- run artifacts and append-only execution history

## Wave 2 - Operator usability and runtime completeness

- review/CI context ingestion
- status and easier outcome recording
- lifecycle side effects such as work-item stage mutation and post-merge hooks

## Wave 3 - Governed autonomous execution

- orchestration substrate decision and implementation
- interrupt/resume model
- event-driven triggers
- guarded auto-promote and auto-merge
- evaluation harness

## Opened First-Wave Child Issues

1. [#196](https://github.com/tomanizer/risk-manager/issues/196) `docs/delivery/github_issue_drafts/agent_runtime_modernization_wave1_01_shared_handoff_bundle.md`
2. [#197](https://github.com/tomanizer/risk-manager/issues/197) `docs/delivery/github_issue_drafts/agent_runtime_modernization_wave1_02_pr_followup_checkout.md`
3. [#198](https://github.com/tomanizer/risk-manager/issues/198) `docs/delivery/github_issue_drafts/agent_runtime_modernization_wave1_03_governed_automated_backends.md`
4. [#199](https://github.com/tomanizer/risk-manager/issues/199) `docs/delivery/github_issue_drafts/agent_runtime_modernization_wave1_04_run_artifacts_and_history.md`

## Why This Needs To Be Tracked As One Initiative

Without an umbrella issue, this work risks becoming a set of disconnected fixes:

- prompt cleanup
- worktree fixes
- backend tweaks
- LangGraph experiments

That would recreate the current problem: many partially overlapping control planes and no authoritative plan.

## Definition Of Done For This Umbrella

This umbrella closes only when:

- the repo has one shared handoff/context contract used by manual and runtime flows
- runtime-managed PR follow-up coding is branch-correct
- automated backends run with governed role instructions
- runtime executions have durable artifacts and meaningful run history
- a clear Wave 2 and Wave 3 plan exists based on what was learned in Wave 1

## Tracking Checklist

- [x] approve repo-local plan structure
- [x] open Wave 1 issue set
- [x] convert the first dependency-wave issues into repo work items
- [ ] complete Wave 1
- [ ] re-plan Wave 2 based on actual runtime changes

## Notes For PM / Issue Planner

- Do not decompose this umbrella issue directly into coding work.
- Use it to manage sequencing, dependencies, and closure criteria.
- Each approved child issue should produce one or more bounded repo work items under `work_items/`.
- Wave 1 `agent_runtime` modernization is tracked in `WI-MAINT-*` items, but implementation should stay manual-direct by default until the Wave 1 foundations are stable enough for selective self-hosting.

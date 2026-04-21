# Agent Runtime Modernization Plan

## Document Status

- Initiative: `agent-runtime-modernization`
- Status: Active
- Owner: PM / Coordination Agent
- Linked audit: [agent_runtime_audit_2026-04-21.md](../../guides/agent_runtime_audit_2026-04-21.md)
- Linked repo-local template: [agent_runtime_modernization_plan_template.md](./agent_runtime_modernization_plan_template.md)
- Linked umbrella issue: [#195](https://github.com/tomanizer/risk-manager/issues/195)
- Last updated: `2026-04-21`

## 1. Problem Statement

The repository currently has three partially overlapping delivery control planes:

1. manual prompt-driven delivery via `skills/deliver-wi/SKILL.md` and `scripts/invoke.py`
2. semi-autonomous supervision via `agent_runtime`
3. an aspirational autonomous path via opt-in backends, LangGraph, parallel dispatch, post-merge hooks, and autonomy flags

Manual invocation currently works best because it has the richest execution context and the clearest governance boundaries. Semi-autonomous runtime mode owns state and worktrees, but it does not yet own the full handoff contract. Automated mode is not yet a real end-to-end operating mode; it is a set of useful but only partially integrated building blocks.

The main modernization goal is not "more automation" in the abstract. The goal is to converge these three paths onto one authoritative runtime model for:

- handoff and context generation
- branch and worktree ownership
- run artifact capture
- PR/review/CI context ingestion
- human gates and resume behavior
- lifecycle side effects after coding, review, and merge

## 2. Outcome Statement By Mode

### Manual

- Reduce operator ceremony without weakening governance boundaries.
- Reuse the same handoff/context contract as the runtime.
- Remove unnecessary copy/paste and shell-quoted state recording where practical.

### Semi-Manual

- Make `agent_runtime` handoffs complete enough that the human is no longer reconstructing execution context manually.
- Make runtime-managed checkout semantics correct for both fresh coding slices and PR-follow-up coding.
- Make runtime state, artifacts, and outcome recording practical to inspect and maintain.

### Autonomous

- Make runs resumable, observable, and policy-gated.
- Preserve explicit human interrupts for repo update and merge decisions unless policy explicitly changes later.
- Ensure automation remains governed by the repository's role-separation model rather than bypassing it.

## 3. Non-Goals

This initiative does not attempt to:

- replace repo governance with a single unconstrained coding agent
- enable auto-merge before review-context ingestion, post-merge hooks, and explicit merge policy gates are in place
- introduce more parallelism before single-PR branch continuity is fixed
- rewrite the runtime around LangChain abstractions before repo-native handoff and state problems are solved
- treat GitHub issues as a substitute for repo-local work items

## 4. Planning Rules

The initiative is planned by shared capability, not by `manual`, `semi-manual`, and `autonomous` as separate workstreams.

Those three modes remain acceptance lenses on each capability.

Working rules:

- keep this file as the repo-local source of truth for sequencing and dependencies
- use GitHub issues for coordination and tracking, not as the canonical execution contract
- decompose only the next dependency wave into bounded implementation work items
- do not start Wave 2 or Wave 3 framework work until Wave 1 foundations are materially complete

## 4A. Execution Policy For Runtime Modernization

Wave 1 runtime-modernization slices are tracked in the normal repo backlog as `WI-MAINT-*` work items.

That does not mean `agent_runtime` should be the default executor for its own modernization work during Wave 1.

Execution policy for this initiative:

- track `agent_runtime` and repo-maintenance modernization slices in `work_items/` using the `WI-MAINT-*` convention
- execute Wave 1 `agent_runtime` modernization slices in manual direct mode by default
- do not use runtime-managed checkout/worktree execution as the default path for runtime-internal changes until the Wave 1 foundations are materially complete
- allow selective self-hosting experiments only after the relevant foundation is stable enough that failures can be attributed clearly to code rather than orchestration ambiguity

Rationale:

- checkout semantics are themselves under repair in Wave 1
- handoff and prompt context are themselves under repair in Wave 1
- run artifact and execution-history behavior are themselves under repair in Wave 1

Using the runtime as the default executor for those same changes too early would create bootstrap ambiguity and make failures harder to diagnose.

## 5. Capability Tracks

| Capability | Problem It Solves | Manual Impact | Semi-Manual Impact | Autonomous Impact | Primary Owner | Depends On | GitHub Tracking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shared handoff bundle | Runtime handoffs are thinner than manual/script-driven prompts | High | High | High | PM for contract, Coding for implementation | None | [#196](https://github.com/tomanizer/risk-manager/issues/196) |
| PR-follow-up checkout semantics | Runtime follow-up coding forks onto a new branch instead of continuing the PR head | None | High | High | Coding Agent | None | [#197](https://github.com/tomanizer/risk-manager/issues/197) |
| Governed automated backends | `codex_exec` does not use the governed role instructions consistently | Low | High | High | Coding Agent with PM review | Shared handoff bundle recommended | [#198](https://github.com/tomanizer/risk-manager/issues/198) |
| Run artifacts and append-only execution history | Runtime keeps last-known state better than full run lineage | Medium | High | High | Coding Agent | Shared handoff bundle recommended | [#199](https://github.com/tomanizer/risk-manager/issues/199) |
| Review/CI context ingestion | Automated review sees too little of the real PR state | Low | Medium | High | Coding Agent with Review input | Shared handoff bundle, run artifacts | Future Wave 2 issue |
| Lifecycle side effects | Work item stage mutation and post-merge hooks exist but are not wired | Medium | Medium | High | Coding Agent with PM input | Run artifacts | Future Wave 2 issue |
| Orchestration substrate decision | Custom loop, parallel dispatch, and LangGraph prototypes coexist without a chosen path | Low | Medium | High | PM / Spec decision, then Coding | Wave 1 foundations | Future Wave 3 issue |

## 6. Wave Plan

## Wave 1 - Foundations

### Purpose

Create the runtime foundations required before operator-usability polish or autonomous orchestration framework work makes sense.

### In Scope

- shared handoff bundle and prompt/context unification
- PR-follow-up checkout semantics for runtime-managed runs
- governed role instructions for automated backends
- run artifacts and append-only execution history

### Entry Criteria

- audit accepted as the baseline
- repo-local plan approved
- umbrella issue approved
- no attempt to solve runtime quality primarily by adding framework

### Exit Criteria

- runtime handoff quality matches or exceeds manual invocation quality for PM, coding, and review
- PR-follow-up coding can operate on the authoritative PR head branch without branch forking
- automated backends run with governed role instructions and explicit execution context
- each runtime execution has durable run artifacts and replayable history

## Wave 2 - Operator Usability And Runtime Completeness

### Purpose

Make the runtime practical to operate day to day once the foundations are trustworthy.

### In Scope

- review/CI context ingestion
- status and easier outcome recording
- lifecycle side effects such as work-item stage mutation and post-merge hooks

### Exit Criteria

- semi-manual runtime operation no longer depends on shell-quoted JSON and ad hoc context recovery
- review and coding follow-up runs have enough PR context to be first-class runtime operations
- runtime-managed lifecycle side effects are explicit, durable, and policy-bound

## Wave 3 - Governed Autonomous Execution

### Purpose

Choose and implement the runtime's long-term orchestration substrate after the foundational state, context, and artifact model are correct.

### In Scope

- orchestration substrate decision and implementation
- interrupt/resume model
- event-driven triggers
- guarded auto-promote and auto-merge
- evaluation and replay harness

### Exit Criteria

- unattended bounded runtime loops are resumable and observable
- human gates remain explicit and auditable
- autonomy is policy-gated rather than implicit

## 7. Wave 1 Exact Issue Set

The approved Wave 1 issue set is:

1. [#196](https://github.com/tomanizer/risk-manager/issues/196) Shared handoff bundle and prompt/context unification
2. [#197](https://github.com/tomanizer/risk-manager/issues/197) PR-follow-up checkout semantics for runtime-managed runs
3. [#198](https://github.com/tomanizer/risk-manager/issues/198) Governed role instructions for automated backends
4. [#199](https://github.com/tomanizer/risk-manager/issues/199) Run artifacts and append-only execution history

These four issues should all be opened at the GitHub level for visibility, but implementation should begin only on the first dependency pair before decomposing the remainder into detailed work items.

## 8. Wave 1 Dependency Order

### Order Of Work

1. Approve repo-local plan.
2. Open the umbrella issue.
3. Open the four Wave 1 child issues.
4. Decompose only issues 1 and 2 into repo work items first.
5. Implement issue 1 and issue 2.
6. Re-run PM / Issue Planner on issues 3 and 4 using what changed in issues 1 and 2.
7. Decompose and implement issues 3 and 4.

Current status on `2026-04-21`:

- repo-local plan instantiated
- umbrella issue opened as [#195](https://github.com/tomanizer/risk-manager/issues/195)
- Wave 1 child issues opened as [#196](https://github.com/tomanizer/risk-manager/issues/196), [#197](https://github.com/tomanizer/risk-manager/issues/197), [#198](https://github.com/tomanizer/risk-manager/issues/198), and [#199](https://github.com/tomanizer/risk-manager/issues/199)
- issues [#196](https://github.com/tomanizer/risk-manager/issues/196) and [#197](https://github.com/tomanizer/risk-manager/issues/197) materialized into repo work items

### Why This Order

- Issue 1 defines the shared handoff contract that later automation should consume.
- Issue 2 fixes a correctness bug in runtime-managed execution.
- Issue 3 should not be finalized until the runtime has a stronger shared handoff contract.
- Issue 4 benefits from the artifact shape chosen for issue 1 and should not force a premature storage model before the handoff bundle is defined.

## 9. Practical Concurrency Guidance

Wave 1 should not be executed as four simultaneous coding efforts.

Recommended concurrency:

- Planning phase:
  - open umbrella and all four child issues in parallel after plan approval
- Coding phase:
  - issues 1 and 2 may be explored in parallel
  - issue 1 should land its bundle/interface contract before issue 3 is fully implemented
  - issue 4 schema/artifact design can be explored in parallel, but final implementation should follow the handoff bundle contract

Practical rule:

- parallelize design and investigation where write scopes are disjoint
- sequence merges where one issue defines the contract another issue consumes

## 10. Recommended Repo Work-Item Conversion Policy

GitHub issues are coordination artifacts. Repo work items are execution artifacts.

When a GitHub issue is approved for implementation:

1. Create or update corresponding bounded work items under `work_items/`.
2. Use `WI-MAINT-*` style identifiers for runtime/delivery-infrastructure work unless the PM agent chooses a different governed convention.
3. Carry over:
   - purpose
   - scope
   - out of scope
   - dependencies
   - target area
   - acceptance criteria
   - review focus
4. Keep each work item bounded enough for one reviewable PR.

### Recommended Initial Conversion

Convert only the following first:

- Issue [#196](https://github.com/tomanizer/risk-manager/issues/196) into 2-3 work items
- Issue [#197](https://github.com/tomanizer/risk-manager/issues/197) into 1-2 work items

Do not convert issues 3 and 4 into detailed work items until issues 1 and 2 have landed or at least stabilized their contracts.

Materialized work items on `2026-04-21`:

- [WI-MAINT-2A](../../../work_items/ready/WI-MAINT-2A-shared-handoff-bundle-contract.md) - ready
- [WI-MAINT-2B](../../../work_items/blocked/WI-MAINT-2B-runtime-shared-handoff-migration.md) - blocked on `WI-MAINT-2A`
- [WI-MAINT-2C](../../../work_items/blocked/WI-MAINT-2C-manual-handoff-surface-parity.md) - blocked on `WI-MAINT-2A` and `WI-MAINT-2B`
- [WI-MAINT-3A](../../../work_items/done/WI-MAINT-3A-runtime-pr-followup-checkout-semantics.md) - done via [PR #194](https://github.com/tomanizer/risk-manager/pull/194)

## 11. Suggested Wave 1 Work-Item Granularity

The following is a planning estimate, not a fixed decomposition.

### Issue 1 - Shared handoff bundle

Expected decomposition:

- one work item for bundle schema and rendering contract
- one work item for runtime migration to the shared builder
- one work item for manual/script surface migration and parity tests

### Issue 2 - PR-follow-up checkout semantics

Expected decomposition:

- one work item for checkout-mode model and worktree-manager implementation
- optional second work item for follow-up doc/test hardening if the first PR gets too broad

### Issue 3 - Governed automated backends

Expected decomposition after Wave 1 midpoint:

- one work item for `codex_exec` governed prompt plumbing
- one optional work item for role coverage and spec-role alignment if needed

### Issue 4 - Run artifacts and history

Expected decomposition after Wave 1 midpoint:

- one work item for run artifact directory and persisted outputs
- one work item for append-only execution history / current-state projection updates

## 12. Acceptance Matrix By Mode

| Capability | Manual Done When | Semi-Manual Done When | Autonomous Done When |
| --- | --- | --- | --- |
| Shared handoff bundle | Manual launcher uses the same bundle as runtime | `--execute` and `--dispatch` emit the full bundle | Automated backends consume the same bundle directly |
| PR-follow-up checkout semantics | Manual guidance stays aligned to real checkout policy | Existing PR follow-up uses the PR head branch | Autonomous repair runs stay on the authoritative PR branch |
| Governed automated backends | Manual role boundaries stay aligned with automated role boundaries | `codex_exec` uses governed role instructions | All automated backends use governed role instructions |
| Run artifacts and history | Manual runs can write/read outcome artifacts | Every runtime run has durable artifacts | Autonomous loops can replay, resume, and audit runs reliably |

## 13. Risks And Open Questions

### Risks

- the runtime may need a new execution-record model rather than small changes to `workflow_runs`
- GitHub review and CI ingestion may require deeper `gh` or GraphQL plumbing than the current sync layer supports
- handoff-bundle migration may touch both runtime and manual surfaces at once, which raises coordination risk
- issue 2 may uncover broader assumptions in branch naming and PR publication logic

### Open Questions

- should the long-term run record live primarily in SQLite, filesystem artifacts, or a hybrid of both
- should `codex_exec` receive governed instructions via a true system surface if available, or via a wrapped user prompt if not
- should the spec runner continue to represent "gap resolution" only, or be renamed and aligned explicitly with the PRD / Spec Author role
- after Wave 1, is the correct orchestration substrate still the custom loop, or should the runtime move to LangGraph for interrupt/resume and fan-out semantics

## 14. Decision Log

| Date | Decision | Reason | Consequence |
| --- | --- | --- | --- |
| `2026-04-21` | Plan by shared capability rather than by operating mode | The main problems are cross-cutting and already duplicated across control planes | Issue tree and work items stay aligned to reusable foundations |
| `2026-04-21` | Treat Wave 1 as a foundations wave, not an autonomy-framework wave | Better scheduling does not fix weak handoffs or incorrect branch semantics | LangGraph and broader autonomy stay out of Wave 1 coding scope |
| `2026-04-21` | Open all four Wave 1 issues, but decompose only the first dependency pair first | This keeps visibility high while preventing front-loaded backlog sprawl | Work-item creation stays bounded and adaptive |

## 15. Immediate Execution Plan

### Next Step

Run a PM / readiness pass for [WI-MAINT-2A](../../../work_items/ready/WI-MAINT-2A-shared-handoff-bundle-contract.md), then start coding on that slice. Treat [WI-MAINT-3A](../../../work_items/done/WI-MAINT-3A-runtime-pr-followup-checkout-semantics.md) as completed foundation work on `main`.

### After Issue Creation

Completed on `2026-04-21`:

- issue [#196](https://github.com/tomanizer/risk-manager/issues/196) materialized into `WI-MAINT-2A`, `WI-MAINT-2B`, and `WI-MAINT-2C`
- issue [#197](https://github.com/tomanizer/risk-manager/issues/197) materialized into `WI-MAINT-3A`

Do not yet create detailed work items for issues [#198](https://github.com/tomanizer/risk-manager/issues/198) and [#199](https://github.com/tomanizer/risk-manager/issues/199).

### First Coding Sequence

1. shared handoff bundle contract and renderer
2. runtime checkout-mode and PR-follow-up branch correctness
3. backend governance plumbing against the new bundle contract
4. durable run artifacts and append-only execution history

## 16. Change Control

Update this plan when:

- a wave boundary changes
- a dependency assumption changes
- a capability is split or merged
- the chosen orchestration direction changes
- the issue-to-work-item strategy changes materially

Do not update this plan merely to mirror day-to-day status noise.

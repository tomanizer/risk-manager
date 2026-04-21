# Agent Runtime Modernization Plan Template

## Document Status

- Initiative: `agent-runtime-modernization`
- Status: Draft
- Owner: PM / Coordination Agent
- Linked audit: `docs/guides/agent_runtime_audit_2026-04-21.md`
- Linked umbrella issue: `<GitHub issue URL or number>`
- Last updated: `<YYYY-MM-DD>`

## How To Use This Template

Use this document as the canonical repo-local implementation plan for a multi-issue delivery initiative.

Rules:

- Keep this file as the source of truth for sequencing, scope boundaries, and dependencies.
- Use GitHub issues for coordination and status, not as the only planning surface.
- Decompose only the next dependency wave into implementation issues and work items.
- Treat `manual`, `semi-manual`, and `autonomous` as acceptance lenses on each capability, not as separate workstreams.

## 1. Problem Statement

Summarize the current problem in one or two paragraphs:

- what is broken today
- why the current workflow is cumbersome
- why this initiative matters now

For `agent_runtime`, the current baseline is:

- manual invocation works best because it has the richest handoff context
- semi-autonomous runtime mode owns state and worktrees but not the full handoff contract
- automated mode is not yet a real end-to-end operating mode

## 2. Outcome Statement By Mode

Define the target outcome for each operating mode.

### Manual

- Reduce operator ceremony without weakening governance boundaries.
- Reuse the same handoff/context contract as the runtime.

### Semi-Manual

- Make `agent_runtime` handoffs complete enough that the human is no longer stitching together context manually.
- Make branch/worktree ownership and outcome recording reliable.

### Autonomous

- Make runs resumable, observable, and policy-gated.
- Preserve explicit human interrupts for repo update and merge decisions unless policy explicitly changes.

## 3. Non-Goals

List the things this initiative will not do.

Suggested starting non-goals:

- replacing repo governance with a single all-purpose coding agent
- enabling auto-merge before review-context ingestion and post-merge hooks are wired
- introducing parallelism before single-PR branch continuity is fixed
- rewriting the runtime around LangChain abstractions without first fixing repo-native handoff and state problems

## 4. Capability Tracks

Plan by shared capability, not by operating mode.

| Capability | Problem It Solves | Manual Impact | Semi-Manual Impact | Autonomous Impact | Depends On | GitHub Issue | Repo Work Items |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shared handoff bundle | Runtime handoffs are thinner than manual/script-driven prompts | High | High | High | None | `<issue>` | `<WI(s)>` |
| PR-follow-up checkout semantics | Runtime follow-up coding forks onto a new branch instead of continuing the PR head | None | High | High | None | `<issue>` | `<WI(s)>` |
| Governed prompts for automated backends | `codex_exec` does not use the governed role instructions | Low | High | High | Shared handoff bundle | `<issue>` | `<WI(s)>` |
| Run artifacts and append-only execution history | The runtime keeps last-known state better than full run lineage | Medium | High | High | Shared handoff bundle | `<issue>` | `<WI(s)>` |
| Review/CI context ingestion | Automated review sees too little of the real PR state | Low | Medium | High | Shared handoff bundle, run artifacts | `<issue>` | `<WI(s)>` |
| Lifecycle side effects | Work item stage mutation and post-merge hooks exist but are not wired | Medium | Medium | High | Run artifacts | `<issue>` | `<WI(s)>` |
| Orchestration substrate decision | The runtime has custom loop, parallel dispatch, and LangGraph prototypes with no single chosen path | Low | Medium | High | Foundations above | `<issue>` | `<WI(s)>` |

## 5. Wave Plan

Sequence by dependency.

## Wave 1 - Foundations

Entry criteria:

- audit reviewed
- umbrella issue approved
- no attempt to solve autonomy by framework swap alone

Target capabilities:

- shared handoff bundle
- PR-follow-up checkout semantics
- governed prompts for automated backends
- run artifacts and append-only execution history

Exit criteria:

- runtime handoff quality matches or exceeds manual invocation quality for PM, coding, and review
- PR follow-up coding can operate on the PR head branch without branch forking
- automated backends run with governed role instructions
- each execution has durable run artifacts and replayable history

## Wave 2 - Operator Usability And Runtime Completeness

Target capabilities:

- review/CI context ingestion
- status and easier outcome recording
- lifecycle side effects

Exit criteria:

- semi-manual runtime operation no longer depends on shell-quoted JSON and ad hoc context recovery
- review and coding follow-up runs have the context they need

## Wave 3 - Autonomous Execution

Target capabilities:

- orchestration substrate decision and implementation
- event-driven triggers
- interrupt/resume model
- guarded auto-promote and auto-merge
- evaluation harness

Exit criteria:

- unattended bounded runtime loops are resumable and observable
- human gates are explicit and auditable

## 6. Current Recommended Issue Breakdown

Use this section to map the current initiative to concrete issue drafts.

Wave 1 recommended issue set:

1. Shared handoff bundle and prompt/context unification
2. PR-follow-up checkout semantics for runtime-managed runs
3. Governed role instructions for automated backends
4. Run artifacts and append-only execution history

## 7. Acceptance Matrix By Mode

Use this table to keep mode goals visible without splitting the backlog by mode.

| Capability | Manual Done When | Semi-Manual Done When | Autonomous Done When |
| --- | --- | --- | --- |
| Shared handoff bundle | Manual launcher uses the same bundle as runtime | `--execute` and `--dispatch` emit the full bundle | Automated backends consume the same bundle directly |
| PR-follow-up checkout semantics | N/A | Existing PR follow-up uses PR head branch | Autonomous repair runs stay on the authoritative PR branch |
| Governed automated backends | N/A | `codex_exec` uses governed role instructions | All automated backends use governed role instructions |
| Run artifacts and history | Manual runs can write/read outcome artifacts | Every runtime run has durable artifacts | Autonomous loops can replay, resume, and audit runs reliably |

## 8. Risks And Open Questions

Track the material planning risks here.

Suggested starting risks:

- the runtime may need a new execution-record model rather than small changes to `workflow_runs`
- GitHub review and CI ingestion may require deeper `gh` or GraphQL plumbing than the current sync layer
- LangGraph may help with orchestration, but adopting it before the run contract is cleaned up could freeze the wrong abstractions

## 9. Decision Log

Record planning decisions in short entries.

| Date | Decision | Reason | Consequence |
| --- | --- | --- | --- |
| `<YYYY-MM-DD>` | Plan by shared capability rather than by mode | The main problems are cross-cutting | Issues and work items stay aligned to reusable foundations |

## 10. Issue-To-Work-Item Conversion Rule

When a GitHub issue is approved for implementation:

1. Create or update the corresponding repo work item under `work_items/`.
2. Carry over:
   - scope
   - out of scope
   - dependencies
   - target area
   - acceptance criteria
   - review focus
3. Do not treat the GitHub issue body as a substitute for the work item.

## 11. Change Control

Update this plan when:

- a wave boundary changes
- a dependency assumption changes
- a capability is split or merged
- a chosen orchestration direction changes

Do not update this plan merely to mirror day-to-day status noise.

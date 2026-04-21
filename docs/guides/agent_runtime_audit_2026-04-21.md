# Agent Runtime Audit - 2026-04-21

## Executive Summary

The main problem is not that the repository lacks agent logic. It is that the repository currently has three partially overlapping control planes:

1. manual prompt-driven delivery via `skills/deliver-wi/SKILL.md` and `scripts/invoke.py`
2. semi-autonomous supervision via `agent_runtime`
3. an aspirational autonomous path via opt-in backends, LangGraph, parallel dispatch, post-merge hooks, and autonomy flags

These three modes do not share one authoritative prompt builder, one authoritative run model, or one authoritative branch/session ownership model.

That fragmentation explains the current operator experience:

- manual invocation works best because it has the richest context and the clearest governance boundaries
- semi-autonomous mode feels cumbersome because it automates worktree/state plumbing but still leaves the human doing session launch, context stitching, and outcome recording
- automated mode is not a real end-to-end operating mode yet; it is a collection of useful building blocks plus a few unwired prototypes

The runtime can get close to autonomous use, but only if it stops being "a poll loop plus subprocesses" and becomes the single authoritative controller for:

- prompt/context assembly
- branch/worktree ownership
- run artifact capture
- PR feedback ingestion
- human gates and resume points
- lifecycle side effects after coding/review/merge

## Scope And Evidence

This audit reviewed:

- `agent_runtime/README.md`
- `agent_runtime/manual_supervisor_workflow.md`
- `agent_runtime/orchestrator/*.py`
- `agent_runtime/runners/*.py`
- `agent_runtime/storage/*.py`
- `agent_runtime/config/*.py`
- `skills/deliver-wi/SKILL.md`
- `scripts/invoke.py`
- relevant guide and prompt files under `docs/guides/` and `prompts/agents/`

Validation performed:

- `python -m agent_runtime --help`
- `python -m pytest agent_runtime/tests/test_autonomous_loop.py agent_runtime/tests/test_supervisor_loop.py agent_runtime/tests/test_parallel_dispatch.py agent_runtime/tests/test_langgraph_readiness.py agent_runtime/tests/test_openai_backend.py -q`

Result:

- targeted runtime tests passed: `57 passed`

## Current State By Operating Mode

### 1. Manual Invocation Mode

### What is working

- The manual path is the best-governed path today.
- `skills/deliver-wi/SKILL.md` forces a fresh session boundary and explicit role separation.
- `scripts/invoke.py` resolves work-item sections, PRD paths, ADRs, and template placeholders into a much richer handoff than the runtime currently produces.
- The manual mode keeps the human in the loop at the right places: scope validation, branch creation, review interpretation, and merge judgment.

### What is painful

- It is copy/paste heavy by design.
- It requires repeated session switching across PM, coding, review, and drift roles.
- The operator has to remember freshness, branch setup, prompt generation, and outcome bookkeeping as separate steps.
- It creates duplicated ceremony:
  - skill-driven prompt building
  - script-driven prompt building
  - runtime-driven prompt building

### Assessment

Manual mode is currently the highest-quality path, but it does not scale operationally. The repo should keep its governance discipline while removing the prompt-copying and state-recording friction.

### 2. Semi-Autonomous Runtime Mode

### What is working

- The transition engine is coherent and deterministic.
- Worktree leasing is a strong foundation.
- SQLite-backed run state, worktree leases, telemetry, and supervisor heartbeat are useful.
- The PM, review, spec, coding, issue-planner, and drift-monitor roles are represented explicitly.
- The runtime already knows how to route ready items, open PRs, review-required PRs, failing CI PRs, backlog-materialization cases, and PRD bootstrap cases.

### What is not working

- The runtime automates scheduling more than execution quality.
- It knows what role should run next, but it does not yet assemble the same quality of context that the manual path provides.
- It still assumes a human will:
  - open the worktree
  - start a new session
  - paste the prompt
  - inspect the answer
  - record the outcome back into SQLite

### Assessment

This mode is currently a coordination bridge, not a convincing operating model. It owns state and worktrees, but not the full handoff contract.

### 3. Automated Mode

### What is present

- optional `codex_exec` backends
- OpenAI and Anthropic structured-output backends for PM/spec/review
- LangGraph prototype
- parallel dispatch prototype
- post-merge hook implementation
- draft PR publication
- autonomy flags in config

### What is missing

- one real CLI path for autonomous execution
- one integrated state machine for dispatch, wait, human interrupt, resume, and side effects
- branch continuity for PR-follow-up coding
- automatic review-comment and CI-log ingestion
- automatic work-item stage mutation
- actual use of `auto_merge`, `auto_promote_wi`, `run_parallel_step`, or `run_post_merge_hooks`

### Assessment

The repo does not yet have an automated delivery system. It has automation ingredients. That is an important distinction.

## Highest-Impact Findings

### Finding 1: The manual and runtime paths use different handoff quality

The manual path resolves rich context from templates and repo artifacts in `scripts/invoke.py`, including WI sections, PRD path resolution, ADR lookup, and placeholder filling. The runtime path uses much thinner prompt builders in `agent_runtime/orchestrator/execution.py`, `agent_runtime/runners/pm_runner.py`, and `agent_runtime/runners/review_runner.py`.

Observed impact:

- manual prompts contain actual scope, target files, out-of-scope, acceptance criteria, and stop conditions
- runtime prompts often contain only work item id, local path, PR number, or a short reason string
- the mode that should become autonomous is currently the mode with the weakest context

Why it matters:

- this is the clearest reason manual invocation performs better than semi-autonomous execution
- better scheduling will not fix weaker handoffs

Recommendation:

- replace all ad hoc runtime prompt builders with a shared "handoff bundle" builder used by:
  - `skills/deliver-wi`
  - `scripts/invoke.py`
  - `agent_runtime --execute`
  - all automatic backends

That shared builder should produce:

- role
- run metadata
- exact execution checkout instructions
- canonical reading list
- resolved PRD path
- resolved ADR list
- WI scope
- target area
- out-of-scope
- acceptance criteria
- stop conditions
- PR context
- review comments and CI context when relevant

### Finding 2: PR-follow-up coding currently allocates a new branch instead of continuing on the PR head

`build_runner_execution()` sets `base_ref` to `origin/<pull_request.head_ref_name>` when a PR exists, but `allocate_worktree()` always creates a new branch with `git worktree add -b <new-branch> ... <base_ref>`.

Observed impact:

- follow-up coding for an existing PR does not naturally update the PR branch
- the operator is pushed into manual recovery or ad hoc git surgery
- the runtime violates the repo's stated runtime-managed checkout policy for PR follow-up work

Why it matters:

- this is a functional blocker for semi-autonomous and autonomous use
- the runtime can open a new PR for greenfield coding, but it cannot cleanly continue a live PR without forking branch lineage

Recommendation:

- distinguish two checkout modes:
  - `new_slice`: create a new branch from `origin/main`
  - `existing_pr_followup`: attach worktree directly to the PR head branch, or create a worktree that tracks the same branch without inventing a second coding branch
- persist `checkout_mode` explicitly in the run metadata
- make PR-follow-up coding impossible to dispatch unless the runtime can prove it is operating on the PR head branch

### Finding 3: `codex_exec` backends do not use the governed system prompts

The OpenAI and Anthropic backends explicitly load `load_system_prompt()` and send it as a system message. The `codex_exec` backends only pass `execution.prompt` plus an output schema wrapper.

Observed impact:

- the most important practical automation path today, `codex_exec`, is also the path least anchored to the canonical role instructions
- runtime quality depends too much on the small prompt built in the execution layer

Why it matters:

- governance boundaries are one of the core reasons this repository uses multiple agent roles
- those boundaries should not disappear when the runtime switches from manual to automated execution

Recommendation:

- wrap `codex exec` prompts with:
  - governed role instruction
  - invocation/handoff bundle
  - output contract
- if the CLI supports a real system-prompt surface, use it
- if not, prepend a clearly delimited governed instruction block and record it with the run artifact

### Finding 4: Review automation does not ingest the information a real review needs

`agent_runtime/orchestrator/github_sync.py` ingests:

- PR number
- URL
- draft flag
- head ref
- updated timestamp
- review decision
- unresolved thread counts
- merge state
- CI rollup state

It does not ingest:

- review comment bodies
- inline review context
- check-run names and logs
- bot comments
- diff summary

Observed impact:

- the runtime can decide that review should happen, but it does not provide enough material for a strong automated review handoff
- a review backend that sees only "Review PR #71" plus a URL is weaker than the documented review process

Recommendation:

- add a `review_context_builder` that fetches:
  - unresolved review threads with bodies and file locations
  - recent top-level PR comments
  - failing check names
  - failing check logs or summarized failure excerpts
  - diff stats and changed-file list
- store that context in a run artifact, not only in memory

### Finding 5: The spec role is still wired to the legacy instruction file

`prompt_loader.py` maps `RunnerName.SPEC` to `prompts/agents/risk_methodology_spec_agent_instruction.md`, while `AGENTS.md` says that legacy role is retained only for backward compatibility and the responsibilities are now covered by the PRD / Spec Author.

Observed impact:

- the runtime's spec role is at risk of drifting from the repo's canonical spec-authoring model

Recommendation:

- re-point the spec runner to the current canonical spec instruction, or split:
  - `spec_gap_resolution`
  - `prd_author`
- do not keep the runtime on a legacy prompt surface if autonomous use is the goal

### Finding 6: Several autonomy features exist but are not wired into the actual runtime path

Examples:

- `langgraph_graph.py` documents `python -m agent_runtime --langgraph`, but the CLI parser in `graph.py` has no `--langgraph` flag
- `parallel_dispatch.py` implements `run_parallel_step()`, but the main loop does not call it
- `post_merge_hooks.py` exists, but nothing invokes `run_post_merge_hooks()`
- `work_item_state.py` exists, but nothing invokes `maybe_advance_work_item_stage()`
- `AgentRuntimeConfig` exposes `auto_merge` and `auto_promote_wi`, but they are not implemented

Observed impact:

- the repo signals autonomy capability that operators cannot actually rely on
- the architecture surface is broader than the operating surface

Recommendation:

- either wire these features into the real loop or explicitly demote them to experimental status
- avoid shipping autonomy flags before the side effects exist

### Finding 7: The run model is still last-known-state oriented, not run-history oriented

`workflow_runs` is keyed by `work_item_id`, so the table stores the latest state for each work item rather than a full run lineage. There is an event table, but it is not the main operational source of truth.

Observed impact:

- weak replay/debugging for long-lived autonomous work
- harder to compare attempt N against attempt N+1
- weak artifact lineage for failed and retried runs

Recommendation:

- promote `run_id` to a first-class execution record
- keep:
  - `workflow_runs` as an append-only execution log keyed by `run_id`
  - `work_item_state` as the current materialized state
  - `workflow_events` as the event stream
- store artifacts per run:
  - prompt bundle
  - model/backend used
  - changed-files manifest
  - outcome payload
  - PR metadata snapshot

### Finding 8: The operator UX is fragmented across skill, script, runtime, and repo docs

The operator currently has to combine:

- `skills/deliver-wi`
- `scripts/invoke.py`
- `agent_runtime --dispatch`
- `agent_runtime --complete-run`
- `agent_runtime/manual_supervisor_workflow.md`
- repo-level freshness and branch rules

Observed impact:

- too many paths to do roughly the same work
- high cognitive load
- easy drift between docs and actual runtime behavior

Recommendation:

- define one operator-facing command family, for example:
  - `agentctl next`
  - `agentctl run`
  - `agentctl review`
  - `agentctl record`
  - `agentctl status`
- keep `skills/` and `scripts/invoke.py` as thin wrappers over the same underlying bundle builder

## Recommendations For Each Operating Mode

## A. Manual Mode Improvements

### Goal

Keep the governance quality of manual invocation while removing the repetitive ceremony.

### Recommended changes

1. Build one canonical handoff bundle generator.
   - This should supersede most of the custom placeholder filling in `scripts/invoke.py`.
   - The bundle should be serializable to JSON and renderable to markdown.

2. Replace copy/paste prompt generation with "openable run packets".
   - Emit:
     - `run.json`
     - `prompt.md`
     - `context.md`
     - `operator_next_steps.txt`
   - Store them under `.agent_runtime/runs/<run_id>/`.

3. Add one-shot outcome recording from a file.
   - Example:
     - `agent_runtime record --run-id ... --outcome-file .agent_runtime/runs/<run_id>/outcome.json`
   - This removes the need for manual `--outcome-details-json` shell quoting.

4. Add a manual launcher abstraction.
   - Even if Codex/Claude opening cannot be fully automated, the runtime should at least print:
     - the exact worktree path
     - exact session name
     - exact prompt path
     - exact role
     - exact model recommendation

5. Add `agent_runtime status`.
   - Show:
     - active run
     - worktree path
     - last backend used
     - unresolved human gates
     - pending review waits

### Expected result

Manual mode becomes the high-trust fallback and training wheels for the automated system, not a separate operating system.

## B. Semi-Autonomous Mode Improvements

### Goal

Make `agent_runtime --dispatch` genuinely useful without requiring a second layer of human glue.

### Recommended changes

1. Fix branch continuity first.
   - This is the top priority.
   - Existing PR follow-up runs must operate on the PR head branch, not a sibling branch.

2. Replace thin runtime prompts with full handoff bundles.
   - PM, review, spec, issue-planner, coding, and drift-monitor should all use the same evidence-rich context contract.

3. Persist a run artifact directory for every dispatch.
   - Include:
     - prompt bundle
     - input snapshot
     - PR metadata snapshot
     - resolved file list
     - backend command line
     - stdout/stderr
     - parsed outcome

4. Make human completion easier.
   - Add:
     - `agent_runtime complete --run-id ... --decision ready --summary-file ...`
     - `agent_runtime complete --run-id ... --from-json ...`

5. Add review-context harvesting.
   - For review and PR-follow-up coding runs, resolve:
     - unresolved threads
     - recent comments
     - failing checks
     - log summaries

6. Wire work-item stage mutation and post-merge hooks.
   - After PM `ready`: optionally move to `in_progress`
   - After blocked outcomes: optionally move to `blocked`
   - After merge: optionally move to `done` and run post-merge drift

7. Keep the runtime authoritative for worktree lifecycle.
   - The user should not have to infer when to release a lease.
   - Introduce lease expiry, active heartbeat, and stale-run cleanup.

### Expected result

Semi-autonomous mode becomes a credible operator workflow instead of a procedural bridge.

## C. Fully Automated Mode Improvements

### Goal

Move from "manual with helpers" to "governed automation with explicit human interrupts".

### Recommended changes

1. Define the automation boundary explicitly.
   - PM: automatable
   - Spec/PRD gap resolution: automatable when bounded
   - Review triage: automatable
   - Coding: automatable with stricter artifact capture
   - Merge: human-gated by default

2. Move to event-driven execution.
   - Triggers:
     - new ready work item
     - PR opened
     - review thread added
     - CI failed
     - CI passed
     - merge completed

3. Treat autonomous runs as resumable workflows, not subprocess calls.
   - A run should survive:
     - process restart
     - machine restart
     - provider timeout
     - human delay

4. Store input snapshots and outputs immutably.
   - This is required for replayability and governance.

5. Add hard policy gates for automatic side effects.
   - No auto-merge until:
     - green checks
     - review outcome `pass`
     - no unresolved threads
     - drift gate clear
   - No auto-promote of work items until:
     - merge is confirmed
     - post-merge hooks completed

6. Introduce an evaluation harness.
   - Use golden scenarios:
     - ready-no-pr
     - PR with failing CI
     - review comments that should route back to coding
     - backlog-materialization trigger
     - spec-required trigger
   - Compare:
     - manual prompt output
     - runtime prompt output
     - automatic backend decisions

### Expected result

Autonomy becomes a controlled execution mode with traceable state transitions, not a collection of optimistic subprocess wrappers.

## LangChain And LangGraph Assessment

## LangGraph: good fit, but only after the run contract is cleaned up

LangGraph would help with:

- durable checkpointing
- explicit interrupt/resume at human gates
- fan-out/fan-in for parallel eligible work
- event streaming and state inspection
- clearer node boundaries for PM/spec/coding/review/human-gate/post-merge

It is a good orchestration substrate for this runtime because the repository already has:

- explicit roles
- explicit states
- explicit human gates
- deterministic transition logic

Recommended use of LangGraph:

- keep `decide_next_action()` and related deterministic policy logic as repo-owned code
- wrap each runner dispatch and side effect as graph nodes
- use interrupts for:
  - human merge
  - human repo update
  - manual review override
- use checkpointing for resume and crash recovery

Do not use LangGraph as an excuse to replace deterministic repo policy with generic agent planning.

## LangChain: optional, not central

LangChain is less compelling here than LangGraph.

It could help with:

- model adapter normalization
- tracing with LangSmith
- structured evaluation harnesses
- retrieval helpers if you later build canon-aware context packing

It is not the main missing piece because the runtime's problems are:

- branch continuity
- handoff quality
- artifact capture
- PR feedback ingestion
- operator UX

Those are control-plane problems, not chain-composition problems.

Recommendation:

- use LangSmith tracing and evaluation if you want observability and comparison across providers
- use LangGraph for stateful orchestration if you choose a framework
- avoid deep adoption of generic LangChain agent abstractions for coding runs

## Better alternatives to "more agent framework"

If you want deeper automation, the stronger design move is:

- richer repo-native handoff bundles
- explicit run artifacts
- reliable branch/worktree semantics
- event-driven orchestration

before adding more framework abstraction.

If you need a workflow engine beyond LangGraph, Temporal would also be a reasonable fit, but it is a much heavier operational commitment.

## Recommended Target Architecture

The target should be:

1. one deterministic policy layer
2. one authoritative run model
3. one authoritative handoff bundle format
4. one authoritative execution checkout model
5. one authoritative artifact store per run
6. one authoritative resume/human-gate mechanism

Practical shape:

- Policy:
  - existing transition logic, improved
- State:
  - current work-item state + append-only runs + append-only events
- Handoff:
  - shared context builder used by manual and automated modes
- Execution:
  - backend adapters for Codex CLI, OpenAI, Anthropic, and manual launch
- Feedback:
  - GitHub PR metadata + review comments + checks + logs
- Side effects:
  - PR publication, work-item stage mutation, post-merge drift, optional merge

## Recommended Delivery Plan

## Phase 1: Make The Current Runtime Trustworthy

Priority: P0

- fix PR-follow-up branch handling
- unify prompt/context generation
- enrich review and coding context with PR comments and CI data
- persist run bundles and backend artifacts
- align spec runner with canonical spec instruction

Success criteria:

- a failed-CI or changes-requested PR can be routed back to coding without branch confusion
- runtime prompt bundle quality matches or exceeds manual invocation quality

## Phase 2: Reduce Human Glue

Priority: P1

- add `agent_runtime status`
- add `agent_runtime record --from-json`
- add launcher-ready run packets
- wire work-item state mutation and post-merge hooks
- make manual supervisor mode file-driven rather than shell-flag driven

Success criteria:

- semi-autonomous mode no longer requires ad hoc shell quoting and prompt copying
- the operator can understand the state of the system from one command

## Phase 3: Introduce Real Autonomous Execution

Priority: P2

- choose orchestration substrate:
  - improved custom loop
  - or LangGraph
- wire event-driven triggers
- implement resumable interrupts and retries
- gate automatic merge and automatic work-item promotion behind explicit policy flags
- add evaluation harness and replay tests

Success criteria:

- the runtime can run unattended for bounded periods
- failures are resumable
- human gates are explicit and auditable
- merge remains governed rather than accidental

## What I Would Not Do Yet

- I would not add more role-specific prompt builders.
- I would not expand parallelism before fixing single-PR branch continuity.
- I would not enable auto-merge before review-context ingestion and post-merge hooks are wired.
- I would not do a broad LangChain rewrite.
- I would not treat `codex_exec` as "good enough" until it uses the governed role instructions and emits proper run artifacts.

## Bottom Line

To get close to autonomous use, the repository should stop optimizing the scheduler first and instead optimize the handoff contract.

The core sequence should be:

1. unify context generation
2. fix branch ownership
3. capture run artifacts
4. ingest PR feedback deeply
5. wire side effects
6. only then choose whether LangGraph should replace the current supervisor loop

That path preserves the repository's governance model while removing the current friction between Codex sessions, manual scripts, and the runtime control plane.

# Agent Runtime

## Purpose

This directory holds repository-delivery automation, not product risk logic.

It is the home for:

- workflow orchestration
- agent handoff state
- isolated git worktree allocation per agent run
- polling and resume behavior
- runner wrappers for PM, spec, coding, and review roles
- local durable state for autonomous delivery loops

## Why this is top-level

This runtime is not part of the product architecture in `src/`.

It should not live under:

- `src/modules/`
- `src/orchestrators/`
- `src/walkers/`

Those paths are reserved for product code.

`agent_runtime/` exists to run the repository's governed delivery loop.

## Initial structure

- `orchestrator/`
- `runners/`
- `storage/`
- `config/`
- `tests/`

## First scope

The first orchestrator is intentionally narrow:

- scan local work-item state
- sync open GitHub PR state into a small typed model
- choose the next action in the relay
- build a typed runner invocation for PM/spec/coding/review
- dispatch that invocation through deterministic local runner adapters
- allocate or reuse an isolated linked git worktree for dispatched runners
- persist the resulting workflow-run state in SQLite
- stop at the human merge gate

It does not yet execute model APIs directly or run as a background daemon.

Live PR sync uses the local `gh` CLI session. If `gh` is unavailable or unauthenticated,
the runtime degrades to filesystem-only work-item decisions and emits a warning.

## Manual simulation

You can test relay decisions without real GitHub state:

```bash
.venv/bin/python -m agent_runtime --list-scenarios
.venv/bin/python -m agent_runtime --simulate ready-no-pr
.venv/bin/python -m agent_runtime --simulate unresolved-review
.venv/bin/python -m agent_runtime --simulate failing-ci-pr
```

## Live relay decision

```bash
.venv/bin/python -m agent_runtime
```

## Supervised loop commands

Run one supervised cycle with repo-level locking and heartbeat persistence:

```bash
.venv/bin/python -m agent_runtime --run-once
```

Run the supervised poll loop:

```bash
.venv/bin/python -m agent_runtime --poll
```

Optional loop settings:

```bash
.venv/bin/python -m agent_runtime --poll --poll-interval-seconds 300 --max-iterations 12
```

The supervisor loop:

- acquires a single-repo lock at `.agent_runtime/supervisor.lock`
- persists heartbeat and last-action state in SQLite
- dispatches one eligible runner per iteration
- continues automatically after completed automatic runs
- sleeps on `wait_for_reviews` and `noop`
- stops cleanly on `human_update_repo`, `human_merge`, prepared manual handoffs, and failed runs

## Build the next runner invocation

```bash
.venv/bin/python -m agent_runtime --execute
```

This records the current decision in `.agent_runtime/state.db` and returns the
typed runner prompt that a later execution layer can hand to the correct agent.

## Dispatch through the local runner adapters

```bash
.venv/bin/python -m agent_runtime --dispatch
```

This builds the runner invocation, routes it through the local deterministic
runner adapter, allocates or reuses a dedicated linked worktree, and persists
both the execution metadata and the runner result.

The lease is intentionally kept active after dispatch so a later execution layer
can continue from the same isolated checkout.

By default the PM runner remains in manual `prepared` mode. You can opt in to
the first real backend by setting:

```bash
export AGENT_RUNTIME_PM_BACKEND=codex_exec
```

Optional PM backend settings:

```bash
export AGENT_RUNTIME_PM_CODEX_BIN=codex
export AGENT_RUNTIME_PM_CODEX_MODEL=gpt-5
```

When enabled, the PM runner uses `codex exec` in the allocated worktree,
requests a structured PM assessment, and persists `ready`, `blocked`, or
`split_required` automatically through the existing workflow outcome path.

The review runner now supports the same opt-in pattern:

```bash
export AGENT_RUNTIME_REVIEW_BACKEND=codex_exec
```

Optional review backend settings:

```bash
export AGENT_RUNTIME_REVIEW_CODEX_BIN=codex
export AGENT_RUNTIME_REVIEW_CODEX_MODEL=gpt-5
```

When enabled, the review runner uses `codex exec` in the allocated worktree,
requests a structured review triage, and persists `pass`,
`changes_requested`, or `blocked` automatically through the existing workflow
outcome path.

The spec runner now supports the same opt-in pattern:

```bash
export AGENT_RUNTIME_SPEC_BACKEND=codex_exec
```

Optional spec backend settings:

```bash
export AGENT_RUNTIME_SPEC_CODEX_BIN=codex
export AGENT_RUNTIME_SPEC_CODEX_MODEL=gpt-5
```

When enabled, the spec runner uses `codex exec` in the allocated worktree,
requests a structured canon-resolution outcome, and persists `clarified`,
`blocked`, or `split_required` automatically through the existing workflow
outcome path.

The coding runner now supports the same opt-in pattern:

```bash
export AGENT_RUNTIME_CODING_BACKEND=codex_exec
```

Optional coding backend settings:

```bash
export AGENT_RUNTIME_CODING_CODEX_BIN=codex
export AGENT_RUNTIME_CODING_CODEX_MODEL=gpt-5
```

When enabled, the coding runner uses `codex exec` in the allocated worktree,
implements the requested slice directly there, and persists `completed`,
`blocked`, or `needs_pm` automatically through the existing workflow outcome
path.

You can also opt in to automatic draft-PR publication after a completed coding
run with no existing PR:

```bash
export AGENT_RUNTIME_CODING_PR_BACKEND=gh_draft
```

Optional draft-PR title prefix:

```bash
export AGENT_RUNTIME_CODING_PR_TITLE_PREFIX='[codex]'
```

When enabled, the runtime:

- checks that the coding branch is ahead of its base ref
- pushes the branch to `origin`
- reuses an existing open PR for that branch if one already exists
- otherwise opens a new draft PR through `gh`
- persists the PR number and URL back into workflow state

## Record the real manual outcome

```bash
.venv/bin/python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status split_required \
  --summary "Need to split WI-1.1.4 before coding."
```

This updates the stored workflow run with the human-reviewed result of the real
PM/spec/coding/review session. Use `--outcome-details-json` when you need a
small structured payload, and `--release-after-complete` when the worktree is
finished.

The runtime now uses completed PM outcomes as control signals:

- `ready` can advance a ready item to coding without asking PM again
- `blocked` or `split_required` can escalate into the spec runner before coding

The runtime now also uses completed spec outcomes as control signals:

- `clarified`, `blocked`, or `split_required` can stop at a human repo-update
  gate until the canon change is reviewed and merged

The runtime now also uses completed review outcomes as control signals until
the PR changes again:

- `changes_requested` can route the work item back to coding
- `pass` or `blocked` can stop at a human repo-update gate instead of rerunning
  review immediately on the same unchanged PR

The runtime now also uses completed coding outcomes as control signals when no
PR exists yet:

- `completed` can stop at a human repo-update gate so the branch/PR can be
  inspected and published
- `blocked` or `needs_pm` can stop at the same human gate instead of rerunning
  coding immediately on the same unchanged work item

When draft-PR publication is enabled, a completed coding run can publish its own
branch and attach the new PR to workflow state immediately, allowing the next
runtime cycle to move straight into PR-aware routing.

## Release a completed runner worktree

```bash
.venv/bin/python -m agent_runtime --release-run <run_id>
```

Use this when a runner has finished and its isolated worktree is no longer
needed.

## Semi-Automatic Supervised Workflow

The current runtime is designed for a semi-automatic loop:

1. Ask the runtime what should happen next and allocate the isolated worktree:

```bash
.venv/bin/python -m agent_runtime --dispatch
```

1. Open the returned `worktree.path` and run the real PM/spec/coding/review agent
manually in that isolated checkout using the returned `runner.prompt`.

1. When that manual agent session finishes, record the reviewed outcome back into
the runtime:

```bash
.venv/bin/python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status split_required \
  --summary "Need to split WI-1.1.4 before coding." \
  --outcome-details-json '{"recommended_next_step":"update_work_item"}'
```

1. If the run is finished and the isolated checkout is no longer needed, release
it in the same step:

```bash
.venv/bin/python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status split_required \
  --summary "Need to split WI-1.1.4 before coding." \
  --release-after-complete
```

This keeps the runtime state authoritative even before real agent API execution
is wired in.

For the detailed operator recipe, see
[manual_supervisor_workflow.md](manual_supervisor_workflow.md).

The live mode now combines:

- filesystem work-item discovery
- open GitHub PR discovery
- unresolved review-thread counts
- review decision state
- latest status-check rollup state

The initial built-in scenarios cover:

- ready item with no PR
- blocked dependency chain
- draft PR waiting for reviews
- unresolved review feedback
- PR ready for human merge
- PR with failing CI that routes to coding
- no runnable work

## Inspecting persisted state

Check workflow runs:

```bash
sqlite3 .agent_runtime/state.db 'select work_item_id, run_id, status, runner_name, runner_status, outcome_status, outcome_summary, completed_at, updated_at from workflow_runs order by updated_at desc;'
```

Check worktree leases:

```bash
sqlite3 .agent_runtime/state.db 'select run_id, work_item_id, runner_name, branch_name, worktree_path, status, created_at, released_at from worktree_leases order by created_at desc;'
```

Check supervisor state:

```bash
sqlite3 .agent_runtime/state.db 'select status, mode, heartbeat_at, last_started_at, last_completed_at, last_action, last_reason, active_run_id, updated_at from supervisor_state;'
```

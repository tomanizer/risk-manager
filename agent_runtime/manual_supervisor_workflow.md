# Manual Supervisor Workflow

## Purpose

This is the bridge workflow between:

- the current runtime control plane
- and future real PM/spec/coding/review agent backend execution

For a hands-off cadence-driven loop, prefer the new supervisor commands in
`agent_runtime --run-once` and `agent_runtime --poll`. This document remains the
operator recipe for the semi-automatic mode.

Use it when you want `agent_runtime` to remain the authoritative supervisor for:

- next-step routing
- worktree isolation
- branch/run tracking
- workflow state persistence

while a human still launches the actual agent session manually.

## What the runtime already owns

The runtime already decides and persists:

- the next relay action
- the target work item
- the runner role to use
- the runner prompt to hand off
- the isolated linked git worktree for that run
- the run id and worktree lease
- the final recorded manual outcome once you complete the run

## What still happens manually

Before real agent API integration lands, a human still does these steps:

- open the allocated worktree
- start the correct PM/spec/coding/review agent
- paste the generated prompt into that session
- inspect the result
- record the reviewed outcome back into the runtime

The first exceptions are the optional PM, review, and coding backends. If
`AGENT_RUNTIME_PM_BACKEND=codex_exec` or
`AGENT_RUNTIME_REVIEW_BACKEND=codex_exec` or
`AGENT_RUNTIME_CODING_BACKEND=codex_exec` is set, those runners can execute
automatically and persist their own structured outcomes.

## End-to-end loop

### 1. Ask the runtime what should happen next

```bash
.venv/bin/python -m agent_runtime --dispatch
```

This returns JSON including:

- `action`
- `work_item_id`
- `runner.name`
- `runner.prompt`
- `worktree.run_id`
- `worktree.branch_name`
- `worktree.path`
- `state_db_path`

If there is no runnable live `ready/` WI, the runtime may still return an
Issue Planner handoff when an implementation-ready PRD names follow-on WI IDs
that have not yet been materialized under the live backlog tree.

If neither a runnable live `ready/` WI nor a backlog-materialization handoff
exists, the runtime may instead return a PRD/spec handoff when the registry
explicitly marks a non-post-MVP PRD gap as the next required slice.

### 2. Move into the allocated worktree

```bash
cd /absolute/path/from/worktree.path
```

Do the real PM/spec/coding/review work only inside that worktree.

### 3. Launch the matching agent manually

Use the returned `runner.name` to decide which agent to run:

- `pm`
- `spec`
- `coding`
- `review`

Paste the returned `runner.prompt` into that agent session.

### 4. Review the agent result

Treat the real agent outcome as authoritative, not the prepared dispatch stub.

Examples:

- PM may return `READY`, `BLOCKED`, or `SPLIT_REQUIRED`
- review may return findings or a pass
- coding may produce a branch/PR or may stop on canon ambiguity
- if `AGENT_RUNTIME_CODING_PR_BACKEND=gh_draft` is enabled, the runtime may
  publish a completed coding branch as a draft PR automatically on dispatch

### 5. Record the reviewed outcome back into the runtime

```bash
.venv/bin/python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status split_required \
  --summary "Need to split WI-1.1.4 before coding." \
  --outcome-details-json '{"recommended_next_step":"update_work_item"}'
```

This updates the persisted workflow run with:

- `runner_status = completed`
- `outcome_status`
- `outcome_summary`
- optional structured `outcome_details`
- `completed_at`

### 6. Release the worktree when the run is finished

```bash
.venv/bin/python -m agent_runtime --release-run <run_id>
```

Or combine completion and release:

```bash
.venv/bin/python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status split_required \
  --summary "Need to split WI-1.1.4 before coding." \
  --release-after-complete
```

### 7. Update repo truth if the agent outcome requires it

Examples:

- PM says `SPLIT_REQUIRED`: update the affected work item or PRD and merge that doc PR
- review finds defects: keep or reopen the coding branch and route back to coding
- coding opens a PR: let the runtime see the new PR state on the next run

The runtime is the supervisor, but the repository remains the final source of truth.

### 8. Rerun the runtime

```bash
.venv/bin/python -m agent_runtime --dispatch
```

This reevaluates the repo after the last completed manual step and allocates the next run.

For completed PM runs, the runtime now uses the recorded outcome as a control
signal:

- `ready` can advance the item to coding on the next dispatch
- `blocked` or `split_required` can stop at a human repo-update gate until the
  work item file changes

For completed review runs, the runtime now uses the recorded outcome until the
PR changes again:

- `changes_requested` can route the item back to coding
- `pass` or `blocked` can stop at a human repo-update gate instead of rerunning
  review on the same unchanged PR

For completed coding runs, the runtime now uses the recorded outcome when no
PR exists yet:

- `completed` can stop at a human repo-update gate so the branch or PR can be
  published
- `blocked` or `needs_pm` can stop at the same human gate instead of rerunning
  coding on the same unchanged work item

## Suggested outcome statuses

The runtime does not yet enforce a closed outcome enum. Use short, stable values such as:

- `ready`
- `blocked`
- `split_required`
- `changes_requested`
- `completed`
- `needs_pm`
- `pass`
- `failed`

Keep them machine-friendly and consistent across runs.

## Inspecting persisted state

Check workflow runs:

```bash
sqlite3 .agent_runtime/state.db 'select work_item_id, run_id, status, runner_name, runner_status, outcome_status, outcome_summary, completed_at, updated_at from workflow_runs order by updated_at desc;'
```

Check worktree leases:

```bash
sqlite3 .agent_runtime/state.db 'select run_id, work_item_id, runner_name, branch_name, worktree_path, status, created_at, released_at from worktree_leases order by created_at desc;'
```

## Operational rules

- keep the control checkout on refreshed `main`; do not do the real agent work there
- one dispatched run should use one worktree
- do not reuse a worktree for a different work item
- do not switch a runtime-managed session back to `main`
- do not allocate another worktree or create another feature branch inside a runtime-managed session
- record the real outcome before releasing the run whenever possible
- release finished worktrees promptly so lease state stays trustworthy

## Why this mode exists

This mode lets the repository use `agent_runtime` as the governed control plane now, before:

- real model API execution
- automatic result parsing
- background scheduling
- LangGraph or OpenAI Agents SDK integration

That keeps the process disciplined early without pretending the runtime already owns agent execution.

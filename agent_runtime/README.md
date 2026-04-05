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
```

## Live relay decision

```bash
.venv/bin/python -m agent_runtime
```

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
- no runnable work

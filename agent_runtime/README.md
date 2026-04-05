# Agent Runtime

## Purpose

This directory holds repository-delivery automation, not product risk logic.

It is the home for:

- workflow orchestration
- agent handoff state
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
runner adapter, and persists both the execution metadata and the runner result.

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

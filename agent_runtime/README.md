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
- represent GitHub/PR state in a small typed model
- choose the next action in the relay
- stop at the human merge gate

It does not yet execute model APIs directly.

## Manual simulation

You can test relay decisions without real GitHub state:

```bash
.venv/bin/python -m agent_runtime --list-scenarios
.venv/bin/python -m agent_runtime --simulate ready-no-pr
.venv/bin/python -m agent_runtime --simulate unresolved-review
```

The initial built-in scenarios cover:

- ready item with no PR
- blocked dependency chain
- draft PR waiting for reviews
- unresolved review feedback
- PR ready for human merge
- no runnable work

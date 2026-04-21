# GitHub Issue Draft

## Suggested Title

Wave 1: add durable run artifacts and append-only execution history to `agent_runtime`

## Suggested Labels

- `agent-runtime`
- `delivery-infra`
- `wave-1`
- `foundation`

## Parent

- Umbrella: [#195](https://github.com/tomanizer/risk-manager/issues/195)
- Linked audit: `docs/guides/agent_runtime_audit_2026-04-21.md`
- Opened as: [#199](https://github.com/tomanizer/risk-manager/issues/199)

## Body

## Problem

The runtime currently persists useful state in SQLite, but the main operational model is still "latest known state per work item" rather than "durable history of executions with replayable artifacts".

That makes it harder to:

- debug retries
- compare attempt N to attempt N+1
- recover after backend failures
- inspect exactly what context and backend output produced a decision

## Why This Belongs In Wave 1

Reliable automation depends on durable artifacts and run lineage. Without that, the runtime remains a convenient dispatcher rather than a trustworthy control plane.

## Scope

- define a durable run artifact layout under `.agent_runtime/`
- persist per-run artifacts such as:
  - rendered handoff bundle
  - backend command metadata
  - stdout/stderr where available
  - parsed outcome payload
  - key PR metadata snapshot where relevant
- move toward append-only execution history keyed by `run_id`
- keep a current-state projection for fast routing, but do not rely on it as the only history
- add inspection commands or documented inspection queries for run history

## Out Of Scope

- automatic merge
- event-driven orchestration framework changes
- full review-comment ingestion if that requires a separate issue

## Dependencies

- shared handoff bundle strongly recommended

## Mode Impact

### Manual

- manual runs can store and replay outcome artifacts instead of relying on shell-quoted summary flags only

### Semi-Manual

- runtime-managed runs become easier to inspect, compare, resume, and complete

### Autonomous

- automated runs gain the durable execution history required for replayability, observability, and policy-gated resume behavior

## Acceptance Criteria

- each runtime execution has a durable artifact directory keyed by `run_id`
- the runtime persists enough information to reconstruct what was asked, what backend ran, and what came back
- execution history is append-only at the run level even if a current-state view remains for routing
- retry analysis across multiple runs for the same work item is possible without reading overwritten state only
- documentation explains where operators inspect run artifacts

## Evidence

- `agent_runtime/storage/sqlite.py`
- `agent_runtime/orchestrator/graph.py`
- `agent_runtime/orchestrator/parallel_dispatch.py`
- `agent_runtime/manual_supervisor_workflow.md`

## Notes For Work-Item Decomposition

Likely split:

1. run artifact directory design
2. append-only execution-history schema changes
3. current-state projection updates
4. inspection tooling and tests

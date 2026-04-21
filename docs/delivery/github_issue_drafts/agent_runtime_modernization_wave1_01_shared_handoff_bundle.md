# GitHub Issue Draft

## Suggested Title

Wave 1: unify manual and runtime handoffs behind a shared handoff bundle

## Suggested Labels

- `agent-runtime`
- `delivery-infra`
- `wave-1`
- `foundation`

## Parent

- Umbrella: [#195](https://github.com/tomanizer/risk-manager/issues/195)
- Linked audit: `docs/guides/agent_runtime_audit_2026-04-21.md`
- Opened as: [#196](https://github.com/tomanizer/risk-manager/issues/196)

## Body

## Problem

The manual path and the runtime path currently build very different handoffs.

Manual invocation through `skills/deliver-wi` and `scripts/invoke.py` resolves:

- linked PRD paths
- ADRs
- scope
- target area
- out of scope
- acceptance criteria
- stop conditions

The runtime path currently builds much thinner prompts that often contain only a work item id, a local path, and a short reason string.

That means the path intended to become autonomous currently has weaker execution context than the manual path.

## Why This Belongs In Wave 1

This is the highest-leverage fix in the whole initiative. Better scheduling and more framework will not fix weak handoffs.

## Scope

- design one shared handoff bundle format used by:
  - `skills/deliver-wi`
  - `scripts/invoke.py`
  - `agent_runtime --execute`
  - automated backend dispatch paths
- include repo-governed fields for:
  - role
  - execution checkout context
  - linked PRD
  - linked ADRs
  - scope
  - target area
  - out of scope
  - acceptance criteria
  - stop conditions
  - PR context when present
- make the bundle serializable so it can be stored as a run artifact

## Out Of Scope

- changing runtime checkout semantics
- review comment ingestion
- orchestration framework migration

## Dependencies

- none; this is a Wave 1 foundation

## Mode Impact

### Manual

- manual launcher and prompt generation stop using a separate, richer context path
- manual runs gain the same structured artifact shape as runtime runs

### Semi-Manual

- `agent_runtime --execute` and `--dispatch` can emit complete, governed handoffs
- humans stop reconstructing missing context by hand

### Autonomous

- automated backends receive a rich, consistent context contract instead of role-specific thin prompts

## Acceptance Criteria

- there is one shared handoff bundle builder in repo code
- PM, coding, review, spec, and issue-planner handoffs can all be rendered from that builder
- the runtime no longer relies on ad hoc thin prompt builders as the primary source of execution context
- the bundle is durable enough to be written to a run artifact directory
- at least one manual surface and one runtime surface are migrated to the shared builder

## Evidence

- `scripts/invoke.py`
- `skills/deliver-wi/SKILL.md`
- `agent_runtime/orchestrator/execution.py`
- `agent_runtime/runners/pm_runner.py`
- `agent_runtime/runners/review_runner.py`

## Notes For Work-Item Decomposition

Likely split:

1. design the handoff bundle schema and renderer
2. migrate manual prompt generation to the shared builder
3. migrate runtime execution generation to the shared builder
4. add tests proving parity for key fields across manual and runtime surfaces

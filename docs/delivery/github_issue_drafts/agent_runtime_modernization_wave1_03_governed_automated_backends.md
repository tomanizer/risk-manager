# GitHub Issue Draft

## Suggested Title

Wave 1: make automated backends run with governed role instructions

## Suggested Labels

- `agent-runtime`
- `delivery-infra`
- `wave-1`
- `foundation`

## Parent

- Umbrella: [#195](https://github.com/tomanizer/risk-manager/issues/195)
- Linked audit: `docs/guides/agent_runtime_audit_2026-04-21.md`
- Opened as: [#198](https://github.com/tomanizer/risk-manager/issues/198)

## Body

## Problem

The OpenAI and Anthropic backends explicitly load governed system prompts. The `codex_exec` path, which is currently the most practical automation path, does not. It relies mostly on the thin `execution.prompt` body plus an output schema wrapper.

That creates a governance gap: the more automated the runtime becomes, the less directly it is anchored to the canonical role instructions.

There is also a prompt-loader gap for some roles: `issue_planner` and `drift_monitor` have runner classes but are not mapped in the governed prompt loader.

## Why This Belongs In Wave 1

If the runtime is going to automate PM, review, coding, spec, issue-planner, or drift-monitor work, it must do so with the governed role surfaces that justify the relay model in the first place.

## Scope

- ensure all automated backends run with governed role instructions
- decide and implement how governed role instructions are supplied to `codex_exec`
- close prompt-loader gaps for supported runner roles
- align the spec role with the current canonical spec-authoring model rather than the legacy compatibility surface when appropriate
- add tests proving governed prompt loading is applied consistently across supported automated backends

## Out Of Scope

- changing the substantive content of the role instructions
- adding new automated roles beyond the current runner set

## Dependencies

- shared handoff bundle recommended, but backend-governance plumbing can begin before full bundle migration if needed

## Mode Impact

### Manual

- manual mode remains the same in day-to-day use, but role alignment across modes improves

### Semi-Manual

- runtime-dispatched automated runs become more trustworthy because they remain role-constrained

### Autonomous

- the runtime can automate role execution without silently collapsing the repo's governance boundaries

## Acceptance Criteria

- `codex_exec` runs with governed role instructions in addition to task-specific execution context
- OpenAI, Anthropic, and `codex_exec` backend behavior is aligned around the same role instruction source of truth
- supported roles in the runtime have prompt-loader coverage
- legacy-vs-current spec instruction mapping is an explicit decision rather than an accidental default
- tests cover prompt loading for all supported automated roles

## Evidence

- `agent_runtime/runners/coding_backend.py`
- `agent_runtime/runners/pm_backend.py`
- `agent_runtime/runners/review_backend.py`
- `agent_runtime/runners/openai_backend.py`
- `agent_runtime/runners/anthropic_backend.py`
- `agent_runtime/runners/prompt_loader.py`

## Notes For Work-Item Decomposition

Likely split:

1. backend-governance contract design
2. `codex_exec` prompt wrapping implementation
3. prompt-loader role coverage and spec role alignment
4. tests and documentation

# Prompt Pack

This directory contains prompt assets for AI agents operating in this repository.

## Structure

| Directory | Purpose |
| --------- | ------- |
| `agents/` | Canonical operating instructions for all agent roles (PM, PRD/spec, issue planner, coding, review, drift monitor) |
| `agents/invocation_templates/` | Per-task prompt templates with placeholders for each agent role |

## Superseded directories

The following directories previously held standalone prompt templates. Their content has been consolidated into the canonical instruction files and invocation templates under `agents/`. Each file now contains a redirect to the canonical source.

| Directory | Superseded by |
| --------- | ------------- |
| `drift_monitor/` | `agents/drift_monitor_agent_instruction.md` + `agents/invocation_templates/drift_monitor_invocation.md` |
| `prd_generation/` | `agents/prd_spec_agent_instruction.md` + `agents/invocation_templates/prd_spec_invocation.md` |
| `issue_decomposition/` | `agents/issue_planner_instruction.md` + `agents/invocation_templates/issue_planner_invocation.md` |
| `pm/` | `agents/pm_agent_instruction.md` + `agents/invocation_templates/pm_invocation.md` |
| `review/` | `agents/review_agent_instruction.md` + `agents/invocation_templates/review_invocation.md` |

## Rules

- Prompts must reinforce architecture boundaries (modules / walkers / orchestrators).
- Prompts must require explicit scope, typed contracts, degraded-case handling, and acceptance criteria.
- Do not embed business policy into prompts — policy belongs in deterministic services.

# Prompt Pack

This directory contains prompt assets for AI agents operating in this repository.

## Structure

| Directory | Purpose |
| --------- | ------- |
| `agents/` | Repo-visible operating instructions for PM, coding, review, issue-planning, methodology-spec, and drift-monitor agents |
| `drift_monitor/` | Prompt template for repo-health and drift audits |
| `prd_generation/` | Prompts for the PRD Author agent |
| `issue_decomposition/` | Prompts for the issue decomposition agent |
| `pm/` | Prompts for the PM / coordination agent |
| `review/` | Prompts for the review agent |

## Rules

- Prompts must reinforce architecture boundaries (modules / walkers / orchestrators).
- Prompts must require explicit scope, typed contracts, degraded-case handling, and acceptance criteria.
- Do not embed business policy into prompts — policy belongs in deterministic services.

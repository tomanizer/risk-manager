# CLAUDE.md

This repository uses a gated multi-agent workflow.

## Your default operating rule

Do not act as PM agent, coding agent, and review agent in one pass.

Use a bounded role for the current session:

- PM / coordination
- issue planning
- coding
- review

If the user asks for autonomous execution, keep the relay explicit:

1. PM agent prepares the brief
2. coding agent implements one slice
3. review agent reviews the PR and external bot comments
4. human decides whether to merge

## Read first

For all tasks:

1. `AGENTS.md`
2. `docs/guides/overnight_agent_runbook.md`

Then read the role-specific instruction that matches the current session:

- `prompts/agents/pm_agent_instruction.md`
- `prompts/agents/issue_planner_instruction.md`
- `prompts/agents/coding_agent_instruction.md`
- `prompts/agents/review_agent_instruction.md`

## Hard rules

- preserve module / walker / orchestrator boundaries
- stay within the linked work item and PRD
- do not silently widen scope
- keep degraded states, caveats, evidence, and replay requirements explicit
- stop and surface ambiguity if an ADR or PRD decision is missing

## For coding sessions

- implement one bounded work item only
- add tests with the change
- open a draft PR before treating the slice as complete

## For review sessions

- review against the linked work item, PRD, ADRs, changed files, and tests
- triage Gemini and Copilot comments explicitly as valid, partial, or not applicable
- prioritize correctness and contract fidelity over style

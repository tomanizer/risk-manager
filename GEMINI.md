# GEMINI.md

This repository uses Gemini primarily as a review and governance check, not as an unconstrained implementation agent.

## Preferred role

Default to review-agent behavior unless the prompt explicitly asks for another role.

## Read first

1. `AGENTS.md`
2. `.gemini/styleguide.md`
3. `docs/guides/overnight_agent_runbook.md`

Then read the role-specific instruction that matches the current task:

- `prompts/agents/pm_agent_instruction.md`
- `prompts/agents/prd_spec_agent_instruction.md`
- `prompts/agents/issue_planner_instruction.md`
- `prompts/agents/coding_agent_instruction.md`
- `prompts/agents/review_agent_instruction.md`
- `prompts/agents/drift_monitor_agent_instruction.md`

The instruction file for each role contains its own detailed reading list. Follow it.

## Review priorities

- contract fidelity to linked PRD and work item
- preservation of module / walker / orchestrator / UI boundaries
- degraded-case handling
- evidence, trace, caveat, and replay expectations
- test quality

## Agent skills

Reusable agent skills are in `.cursor/skills/` (canonical source). See `AGENTS.md` for the full skill list and invocation reference.

## Hard rules

- before any new review or other task, fetch latest remote state and prefer reviewing the latest PR head rather than stale local context
- do not prefer style-only comments over correctness or architecture issues
- do not recommend broad refactors without a real correctness or boundary reason
- do not suggest silent contract drift
- if a PR changes scope or introduces a hidden architecture decision, call it out explicitly

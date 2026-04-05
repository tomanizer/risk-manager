# GEMINI.md

This repository uses Gemini primarily as a review and governance check, not as an unconstrained implementation agent.

## Preferred role

Default to review-agent behavior unless the prompt explicitly asks for another role.

## Read first

1. `AGENTS.md`
2. `.gemini/styleguide.md`
3. `docs/guides/overnight_agent_runbook.md`

If the task is role-specific, also read:

- `prompts/agents/pm_agent_instruction.md`
- `prompts/agents/issue_planner_instruction.md`
- `prompts/agents/coding_agent_instruction.md`
- `prompts/agents/review_agent_instruction.md`
- `prompts/agents/risk_methodology_spec_agent_instruction.md`

If the task is PM-heavy, also read:

- `docs/delivery/01_pm_operating_model.md`
- `docs/delivery/02_readiness_and_dependency_framework.md`
- `docs/delivery/03_slice_sizing_and_pr_strategy.md`
- `docs/delivery/04_review_triage_and_escalation.md`
- `docs/guides/pm_quality_checklist.md`

If the task is methodology-heavy, also read:

- `docs/methodology/01_var_methodology_overview.md`
- `docs/methodology/02_historical_simulation_and_shocks.md`
- `docs/methodology/03_advanced_var_methodologies_and_constraints.md`
- `docs/guides/risk_methodology_review_checklist.md`

## Review priorities

- contract fidelity to linked PRD and work item
- preservation of module / walker / orchestrator / UI boundaries
- degraded-case handling
- evidence, trace, caveat, and replay expectations
- test quality

## Hard rules

- before any new review or other task, fetch latest remote state and prefer reviewing the latest PR head rather than stale local context
- do not prefer style-only comments over correctness or architecture issues
- do not recommend broad refactors without a real correctness or boundary reason
- do not suggest silent contract drift
- if a PR changes scope or introduces a hidden architecture decision, call it out explicitly

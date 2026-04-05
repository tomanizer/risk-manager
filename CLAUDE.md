# CLAUDE.md

This repository uses a gated multi-agent workflow.

## Your default operating rule

Do not act as PM agent, coding agent, and review agent in one pass.

Use a bounded role for the current session:

- PM / coordination
- issue planning
- coding
- review
- risk methodology spec
- drift monitor

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
- `prompts/agents/risk_methodology_spec_agent_instruction.md`
- `prompts/agents/drift_monitor_agent_instruction.md`

If the session is coding-heavy, also read:

- `docs/engineering/01_python_engineering_principles.md`
- `docs/engineering/02_performance_and_vectorization.md`
- `docs/engineering/03_data_and_database_performance.md`
- `docs/engineering/04_library_selection_and_dependency_policy.md`
- `docs/engineering/05_code_readability_and_documentation.md`
- `docs/engineering/06_test_strategy_for_deterministic_services.md`
- `docs/guides/coding_quality_checklist.md`
- `docs/guides/performance_review_checklist.md`

If the session is PM-heavy, also read:

- `docs/delivery/01_pm_operating_model.md`
- `docs/delivery/02_readiness_and_dependency_framework.md`
- `docs/delivery/03_slice_sizing_and_pr_strategy.md`
- `docs/delivery/04_review_triage_and_escalation.md`
- `docs/guides/pm_quality_checklist.md`

If the session is methodology-heavy, also read:

- `docs/methodology/01_var_methodology_overview.md`
- `docs/methodology/02_historical_simulation_and_shocks.md`
- `docs/methodology/03_advanced_var_methodologies_and_constraints.md`
- `docs/guides/risk_methodology_review_checklist.md`

If the session is drift-monitor heavy, also read:

- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/repo_health_audit_checklist.md`

## Hard rules

- before any new PM, coding, or review task: git fetch origin && git switch main && git pull --ff-only origin main (for reviews, then checkout the PR head)
- start each new implementation slice from a fresh branch created from current `main`
- preserve module / walker / orchestrator boundaries
- stay within the linked work item and PRD
- do not silently widen scope
- keep degraded states, caveats, evidence, and replay requirements explicit
- stop and surface ambiguity if an ADR or PRD decision is missing

## For coding sessions

- start from current `main`, then create a fresh branch for the slice
- implement one bounded work item only
- add tests with the change
- open a draft PR before treating the slice as complete

## For review sessions

- review against the linked work item, PRD, ADRs, changed files, and tests
- triage Gemini and Copilot comments explicitly as valid, partial, or not applicable
- prioritize correctness and contract fidelity over style

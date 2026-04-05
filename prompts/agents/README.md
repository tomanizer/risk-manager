# Agent Instruction Documents

## Purpose

This folder holds repo-visible operating instructions for the repository's main delivery agents and repo-health control agents.

These instructions complement the canon, PRDs, ADRs, prompts, and work items. They do not replace them.

## Files

- `pm_agent_instruction.md`
- `coding_agent_instruction.md`
- `review_agent_instruction.md`
- `issue_planner_instruction.md`
- `risk_methodology_spec_agent_instruction.md`
- `drift_monitor_agent_instruction.md`

## Rule

If a local artifact conflicts with a broader artifact, prefer the more local implementation artifact and record the ambiguity explicitly:

1. work item
2. linked PRD
3. linked ADR
4. local module or workflow documentation
5. repo-wide canon

For PM work, also use:

- `docs/delivery/`
- `docs/guides/pm_quality_checklist.md`

For drift-monitor work, also use:

- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/repo_health_audit_checklist.md`

For coding work, also use:

- `docs/engineering/`
- `docs/guides/coding_quality_checklist.md`
- `docs/guides/performance_review_checklist.md`

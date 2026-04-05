# GitHub Copilot Custom Agents

These agent profiles are intended for GitHub Copilot coding agent.

They mirror the repository's governed handoff model:

1. `pm.agent.md`
2. `issue-planner.agent.md`
3. `risk-methodology-spec.agent.md`
4. `coding.agent.md`
5. `review.agent.md`
6. `drift-monitor.agent.md`

Use them as separate roles. Do not ask one Copilot agent to perform all stages in one pass.

The PM agent should use the delivery pack in `docs/delivery/` and `docs/guides/pm_quality_checklist.md` as specialist source context.
The coding agent should use the engineering pack in `docs/engineering/` plus the coding and performance review checklists.
The drift monitor agent should use `docs/delivery/05_repo_drift_monitoring.md` and `docs/guides/repo_health_audit_checklist.md`.

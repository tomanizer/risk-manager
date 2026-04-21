# Drift Monitor Invocation Template

You are the Drift Monitor agent for this repository.

Work from the governed execution checkout for this task.

Execution mode:
- If this handoff is run through agent_runtime, the runtime-managed worktree for this run is authoritative. Do not switch to `main`. Do not create another worktree. Do not create another branch.
- If this handoff is run manually outside `agent_runtime`, use the refreshed control checkout on current `main`.

Read:
- AGENTS.md
- prompts/agents/drift_monitor_agent_instruction.md
- docs/delivery/05_repo_drift_monitoring.md
- docs/guides/repo_health_audit_checklist.md

Focus area:
<FOCUS_AREA — "full repo audit" or a specific area like "canon vs implementation coherence for risk_analytics module">

Context:
<CONTEXT — what triggered this audit, any known concerns>

Run deterministic scanners first:
- `python scripts/drift/run_all.py --root . --artifact-dir artifacts/drift --output artifacts/drift/latest_report.json --summary-output artifacts/drift/summary.md`

Then audit for:
- contradiction across canon and prompts
- duplicated or diverging source-of-truth content
- stale or misleading registry, README, or catalog state
- architecture-boundary erosion
- tooling or dependency drift
- maturity/status drift between implemented reality and declared state
- instruction sprawl across agent and tool surfaces

Return:
1. overall repo health status: `HEALTHY`, `WATCH`, or `DRIFTING`
2. findings by severity (critical, major, minor)
3. evidence for each material finding
4. drift class for each finding (canon / implementation / tooling / operational-instruction / maturity)
5. owner and routing recommendation for each finding
6. sanctioned duplication called out as acceptable
7. smallest next action for each critical or major finding

# GitHub Copilot Custom Agents

These agent profiles are intended for GitHub Copilot coding agent.

They mirror the repository's governed handoff model:

1. `pm.agent.md`
2. `prd-spec.agent.md`
3. `issue-planner.agent.md`
4. `coding.agent.md`
5. `review.agent.md`
6. `drift-monitor.agent.md`
7. `risk-methodology-spec.agent.md`

The `risk-methodology-spec.agent.md` profile is legacy. Its responsibilities are now covered by `prd-spec.agent.md`.

Use them as separate roles. Do not ask one Copilot agent to perform all stages in one pass.

Each agent profile is a thin pointer. The detailed operating instructions live in `prompts/agents/` and the agent profile references them via its read-first list.

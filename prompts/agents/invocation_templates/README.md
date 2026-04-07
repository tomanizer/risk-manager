# Agent Invocation Templates

These templates define the expected prompt shape for each agent role when invoked for a specific task.

They bridge the standing instruction files (in `prompts/agents/`) with the per-task context an operator provides at invocation time.

## Usage

1. Copy the relevant template
2. Fill in the placeholders (marked with `<PLACEHOLDER>`)
3. Paste as the prompt to the agent in your tool of choice

The agent's standing instruction file is referenced in each template. The agent should read it first, then apply the task-specific context from the invocation prompt.

When a task touches cross-cutting infrastructure, include:

- `docs/shared_infra/index.md`
- relevant files from `docs/shared_infra/` (for example `telemetry.md`)

in the invocation "Read" section so all roles remain aligned on shared
contracts and adoption sequencing.

For the `<RELEVANT_SHARED_INFRA_DOCS>` placeholder: provide repo-relative paths
to canon files (typically under `docs/shared_infra/`), **one path per line**,
replacing the whole placeholder in the Read list. If shared infrastructure is
**not** relevant to the task, substitute `none` for the placeholder, or omit
that Read bullet when your tool allows a shorter invocation.

## Templates

| Template | Agent Role |
| --- | --- |
| `pm_invocation.md` | PM / Coordination Agent |
| `prd_spec_invocation.md` | PRD / Spec Author Agent |
| `issue_planner_invocation.md` | Issue Planner Agent |
| `coding_invocation.md` | Coding Agent |
| `review_invocation.md` | Review Agent |
| `drift_monitor_invocation.md` | Drift Monitor Agent |

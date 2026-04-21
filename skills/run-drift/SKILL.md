---
name: run-drift
description: Produces a filled Drift Monitor invocation prompt when the user says things like "run drift", "audit the repo", "check repo health", or "run the drift monitor". Does NOT run the audit itself.
---

# run-drift

> **HARD CONSTRAINT — read this before anything else.**
>
> This skill NEVER runs the drift audit itself, NEVER edits files, and NEVER executes scripts.
> Its only job is to produce a filled, copy-paste-ready invocation prompt for the Drift Monitor agent.
> The user pastes that prompt into a **separate** fresh agent session to do the actual audit.
> If you feel tempted to start auditing or editing — stop. Produce the prompt instead.

## Mandatory first output

Before doing anything else, print this exact line so the user knows the skill is active:

```text
[run-drift] Skill active. Building drift monitor prompt...
```

## Step 1 — Determine focus area

If the user named a specific area (e.g. "audit risk_analytics", "check the walkers"), use that as the focus area.
Otherwise default to `"full repo audit"`.

## Step 2 — Read context

Read the following files to understand what the audit covers:

- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/repo_health_audit_checklist.md`

## Step 3 — Fill the invocation template

Read `prompts/agents/invocation_templates/drift_monitor_invocation.md`.

Replace the placeholders as follows:

- `<FOCUS_AREA — "full repo audit" or a specific area like "canon vs implementation coherence for risk_analytics module">` → the focus area from Step 1
- `<CONTEXT — what triggered this audit, any known concerns>` → `"Triggered by: [what the user said]. Recent merges: [paste the output of: git log --oneline -5]."`

For the recent-merges part: ask the user to run `git log --oneline -5` and paste the output.
If the user does not provide it, use the literal placeholder `[run: git log --oneline -5]` in the context field so the agent session that receives the prompt can fill it in.

## Step 4 — Print the filled prompt as one fenced block

The first two lines of the block are always the session header and the recommended model.

```text
Paste this into a FRESH Drift Monitor agent session (new chat / new Codex session):
Recommended model: Sonnet (or equivalent mid-tier)

[complete filled drift_monitor_invocation.md content with all placeholders replaced]
```

## Step 5 — Add the freshness reminder

After the prompt block, always print:

```text
Before the agent starts, refresh the control checkout:
  git fetch origin && git switch main && git pull --ff-only origin main
If using agent_runtime:
  python -m agent_runtime --dispatch
  Then use only the returned worktree path and checkout context for that run.
If running manually outside agent_runtime:
  Run the drift monitor from the refreshed control checkout on main.
```

## Hard stops

- STOP if you are about to run the drift audit yourself.
- STOP if you are about to edit or create any source or documentation file.
- STOP if you are about to execute any scripts or shell commands.
- In all of these cases: produce the filled invocation prompt and hand it to the user instead.

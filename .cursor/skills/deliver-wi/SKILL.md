---
name: deliver-wi
description: Drives delivery of a risk-manager work item through the PM → Coding → Review relay. Use when the user wants to work on a work item, implement a WI, run the PM agent, invoke the coding agent, invoke the review agent, advance a work item, or asks what to do next. Produces a filled invocation prompt for the correct specialist agent — does NOT implement anything itself.
---

# deliver-wi

> **HARD CONSTRAINT — read this before anything else.**
>
> This skill NEVER implements code, writes tests, edits source files, or does PM/review work itself.
> Its only job is to identify the next work item and produce a filled, copy-paste-ready invocation prompt for the correct specialist agent (PM, Coding, Review, Issue Planner, or PRD/Spec Author).
> The user pastes that prompt into a **separate** fresh agent session to do the actual work.
> If you feel tempted to start implementing — stop. Produce the prompt instead.

## Mandatory first output

Before doing anything else, print this exact line so the user knows the skill is active:

```text
[deliver-wi] Skill active. Finding next work item and building agent prompt...
```

## Step 1 — Identify the work item

If the user named a specific WI, use it. Otherwise:

1. List `work_items/ready/` to find all ready items.
2. List `work_items/done/` to see what is complete.
3. Pick the lowest-numbered ready item whose dependencies are all present in `done/`.
4. Tell the user which WI was selected and why, then continue.

## Step 2 — Read the required files

Read these files for the chosen WI:

| File | What to extract |
|------|-----------------|
| `work_items/ready/<WI-ID>-*.md` | scope, out-of-scope, target area, dependencies, acceptance criteria, stop conditions, suggested agent |
| The linked PRD path named in the WI | contract details |
| `AGENTS.md` | role definitions and relay rules |

Also read any ADR files listed in the WI's dependencies section.

## Step 3 — Choose the agent role

| Situation | Role | Template |
|-----------|------|----------|
| WI not yet PM-assessed / no implementation brief | PM | `prompts/agents/invocation_templates/pm_invocation.md` |
| PM confirmed READY, no branch yet | Coding | `prompts/agents/invocation_templates/coding_invocation.md` |
| Draft PR exists, needs review | Review | `prompts/agents/invocation_templates/review_invocation.md` |
| WI too broad / PM said SPLIT_REQUIRED | Issue Planner | `prompts/agents/invocation_templates/issue_planner_invocation.md` |
| PRD gap blocking the WI | PRD/Spec Author | `prompts/agents/invocation_templates/prd_spec_invocation.md` |

Default to **PM** when in doubt — it is always safe to run PM first.

## Step 4 — Fill the template

Read the selected template file. Replace every `<PLACEHOLDER>` with the actual value from the WI and PRD.

### PM placeholder mapping

- `<LINKED_PRD>` → path to the PRD file
- `<TARGET_WORK_ITEM>` → path to the WI file
- `<LINKED_ADRS>` → ADR paths from WI dependencies (one per line)
- `<CONTEXT>` → "Done so far: [WI IDs from done/]. Assessing [WI-ID] for coding readiness."
- `<TASK>` → "Assess whether [WI-ID] is coding-ready. Return READY with implementation brief, BLOCKED with exact blocker, or SPLIT_REQUIRED with proposed items."

### Coding placeholder mapping

- `<LINKED_PRD>` → path to PRD
- `<ASSIGNED_WORK_ITEM>` → path to WI file
- `<LINKED_ADRS>` → ADR paths
- `<WORK_ITEM_ID>` → e.g. `WI-1.1.4`
- `<BULLETED_SCOPE_LIST>` → scope section from WI, verbatim
- `<TARGET_FILES>` → target area from WI
- `<BULLETED_OUT_OF_SCOPE>` → out-of-scope from WI, verbatim
- `<BULLETED_ACCEPTANCE_CRITERIA>` → acceptance criteria from WI, verbatim
- `<BULLETED_STOP_CONDITIONS>` → stop conditions from WI, verbatim

### Review placeholder mapping

- `<ASSIGNED_WORK_ITEM>` → path to WI file
- `<LINKED_PRD>` → path to PRD
- `<LINKED_ADRS>` → ADR paths
- `<PR_NUMBER>` → ask user if unknown
- `<BRANCH_NAME>` → ask user if unknown
- `<CONTEXT>` → "This PR implements [WI-ID]: [WI purpose one-liner]."

## Step 5 — Output the filled prompt

Print the filled prompt in a fenced code block with this header above it:

```text
Paste this into a FRESH [Role] agent session (new chat / new Codex session):
```

The user copies this and pastes it into a new chat. You do not act on it.

## Step 6 — Add the freshness reminder

After the prompt block, always print:

```text
Before the agent starts:
  git fetch origin && git switch main && git pull --ff-only origin main
For coding: create a fresh branch from main.
For review: checkout the PR head branch.
```

## Step 7 — Optionally suggest agent runtime tracking

Suggest this only if the user asks about tracking state:

```bash
# Before handing off:
python -m agent_runtime --dispatch

# After the agent session completes:
python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status <ready|completed|changes_requested|blocked> \
  --summary "one-line summary"
```

## Hard stops

- STOP if you are about to write, edit, or create any source file.
- STOP if you are about to run tests or execute implementation commands.
- STOP if you are about to do PM reasoning yourself instead of building the PM prompt.
- In all of these cases: produce the filled invocation prompt and hand it to the user instead.

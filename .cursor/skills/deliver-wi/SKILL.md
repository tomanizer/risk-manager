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

## Mandatory freshness gate (before selecting any WI)

Before Step 0/1 logic, verify branch freshness explicitly:

1. `git fetch origin`
2. `git switch main`
3. `git pull --ff-only origin main`

If any command fails, STOP and tell the user exactly what failed. Do not select a work item from stale state.

Then perform WI discovery from this refreshed `main` checkout only.

## Step 0 — Handle a just-merged PR (short-circuit)

If the user says something like "PR #X is merged", "PR for WI-X.Y.Z was merged", or "just merged PR #X":

Do not run `git mv` or open commits yourself. Route WI lifecycle handling through the PM handoff using the current repository instructions.

Instead, fill `prompts/agents/invocation_templates/pm_invocation.md` and print one block:

```text
Paste this into a FRESH PM Agent session (new chat / new Codex session):
Recommended model: Sonnet (or equivalent mid-tier)

You are the PM / Coordination Agent for this repository.

Work from current `main`.

Read in order:
- AGENTS.md
- prompts/agents/pm_agent_instruction.md
- work_items/READY_CRITERIA.md
- [path to the WI file that was just merged (if still in ready/) or the done/ path if already promoted]

Context:
PR #[PR number] implementing [WI-ID] has been merged. Confirm WI lifecycle state (`ready/` vs `done/`) on current main and perform any required lifecycle action before assessing the next item.

Task:
1. Reconcile WI lifecycle state for [WI-ID] according to current repo instructions (promote if required; otherwise confirm already promoted).
2. Then assess the next ready work item and produce an implementation brief.
```

Do not proceed to Step 1 until the user confirms the PM session is complete or asks to continue.

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
| User asks for a repo health / governance audit | Drift Monitor | `prompts/agents/invocation_templates/drift_monitor_invocation.md` |

Default to **PM** when in doubt — it is always safe to run PM first.

## Step 4 — Fill the template

Read the selected template file. Replace the **exact bracketed placeholder string as written in the template** — including any descriptive suffix (e.g. `<CONTEXT — what has changed>` and `<CONTEXT>` are the same placeholder; replace whichever form appears).

### PM placeholder mapping

- `<LINKED_PRD>` → path to the PRD file
- `<TARGET_WORK_ITEM>` → path to the WI file
- `<LINKED_ADRS>` → ADR paths from WI dependencies (one per line)
- `<CONTEXT>` → "Done so far: [WI IDs from done/]. Assessing [WI-ID] for coding readiness."
- `<TASK>` → "Assess whether [WI-ID] is coding-ready. Return READY with implementation brief, BLOCKED with exact blocker, or SPLIT_REQUIRED with proposed items."

### Coding placeholder mapping

Use the PM implementation brief when one exists from a prior PM session. Fall back to the WI file verbatim only when invoking coding directly without a prior PM pass.

- `<LINKED_PRD>` → path to PRD
- `<ASSIGNED_WORK_ITEM>` → path to WI file
- `<LINKED_ADRS>` → ADR paths
- `<WORK_ITEM_ID>` → e.g. `WI-1.1.4`
- `<BULLETED_SCOPE_LIST>` → scope from PM brief (if available) or WI file
- `<TARGET_FILES>` → target area from PM brief (if available) or WI file
- `<BULLETED_OUT_OF_SCOPE>` → out-of-scope from PM brief (if available) or WI file
- `<BULLETED_ACCEPTANCE_CRITERIA>` → acceptance criteria from PM brief (if available) or WI file
- `<BULLETED_STOP_CONDITIONS>` → stop conditions from PM brief (if available) or WI file

### Review placeholder mapping

- `<ASSIGNED_WORK_ITEM>` → path to WI file
- `<LINKED_PRD>` → path to PRD
- `<LINKED_ADRS>` → ADR paths
- `<PR_NUMBER>` → ask user if unknown
- `<BRANCH_NAME>` → ask user if unknown
- `<CONTEXT>` → "This PR implements [WI-ID]: [WI purpose one-liner]."

## Step 5 — Output the filled prompt

Print the filled prompt as one fenced block. The first two lines of the block are always the session header and the recommended model. Use this model table:

| Role | Recommended model |
|------|------------------|
| PM | Sonnet (or equivalent mid-tier) |
| Issue Planner | GPT-4 mini or Composer (cheapest available) |
| Coding | Sonnet (consider bumping to Opus / GPT-5.4 for complex WIs or after a failed review) |
| Review | Sonnet (or equivalent mid-tier) |
| PRD/Spec Author | Sonnet (consider bumping to Opus / GPT-5.4 for methodology-heavy specs) |
| Drift Monitor | Sonnet (or equivalent mid-tier) |

The block shape is:

```text
Paste this into a FRESH [Role] agent session (new chat / new Codex session):
Recommended model: [model from table above]

[complete filled invocation template content]
```

The user opens a new chat, selects the recommended model, then pastes the whole block. You do not act on it.

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
  --outcome-status <ready|completed|pass|changes_requested|blocked|split_required|needs_pm> \
  --summary "one-line summary"
```

## Hard stops

- STOP if you are about to write, edit, or create any source file.
- STOP if you are about to run tests or execute implementation commands.
- STOP if you are about to do PM reasoning yourself instead of building the PM prompt.
- In all of these cases: produce the filled invocation prompt and hand it to the user instead.

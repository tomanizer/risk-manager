---
name: repo-status
description: Prints a structured, read-only situational awareness dashboard. Use when the user says things like "repo status", "what's the status", "morning check", "what's in progress", or "what should I work on".
---
<!-- GENERATED SKILL MIRROR: do not edit directly -->


# repo-status

> **HARD CONSTRAINT — read this before anything else.**
>
> This skill NEVER invokes an agent, NEVER edits files, NEVER opens PRs, and NEVER writes anything to disk.
> It is purely read-and-report.
> If you feel tempted to do anything other than read and report — stop. Print the dashboard and the action recommendation instead.

## Mandatory first output

Before doing anything else, print this exact line so the user knows the skill is active:

```text
[repo-status] Skill active. Reading repo state...
```

## Step 1 — Read backlog

1. List all files in `work_items/ready/` and `work_items/done/`.
2. For each file, extract the WI ID from the filename and the one-line title from its `## Purpose` section.
3. Build two lists: Done WIs and Ready WIs.

## Step 2 — Read open PRs

Run both of these commands and capture the output:

```bash
gh pr list --state open
gh pr list --state merged --limit 3
```

## Step 3 — Read CI

Run this command and summarise the outcomes:

```bash
gh run list --limit 5 --branch main
```

## Step 4 — Print dashboard

Print the dashboard in this exact shape (fill in each field from the data gathered above):

```text
--- Repo Status ---
Phase        : <current phase from docs/roadmap/phased_implementation_roadmap.md>
Done WIs     : <count> — <comma-separated WI IDs>
Ready WIs    : <count> — <comma-separated WI IDs>
Open PRs     : <count> — <list titles and numbers>
Recent CI    : <pass/fail summary for last 5 runs on main>
Suggested next : <lowest-numbered ready WI with all dependencies in done/>
---
```

To determine the current phase, read `docs/roadmap/phased_implementation_roadmap.md` and match the
in-flight WI IDs to the phase they belong to.

The **Suggested next** field must be the lowest-numbered WI in `work_items/ready/` whose dependencies
are all present in `work_items/done/`. If no such item exists, print
`none — all ready items have unmet dependencies`.

## Step 5 — Recommend action

Print one sentence telling the user what to do next. Examples:

- `Run the deliver-wi skill to get the PM prompt for WI-1.1.7.`
- `All ready items are blocked — consider running the deliver-wi skill to create or unblock the next WI.`
- `No ready work items found — use deliver-wi to plan the next slice.`

## Hard stops

- STOP if you are about to write, edit, create, or delete any file.
- STOP if you are about to invoke another agent or open a PR.
- STOP if you are about to run any command other than the read-only `gh` commands listed above.
- In all of these cases: print only the dashboard and the action recommendation.

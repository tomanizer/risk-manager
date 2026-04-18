---
name: phase-review
description: Produces a go/no-go gate-check checklist for a delivery phase. Use when the user says "phase review", "check if phase N is done", "are we ready for phase N+1", or "review the phase". Reads and reports only — never edits files or creates work items.
---
<!-- GENERATED SKILL MIRROR: do not edit directly -->


# phase-review

> **HARD CONSTRAINT — read this before anything else.**
>
> This skill NEVER implements fixes, edits files, or creates work items.
> It reads repository artefacts and reports a gate-check checklist only.
> If gaps are found it optionally produces a filled PM agent prompt for the user to paste into a separate session.
> If you feel tempted to fix something — stop. Produce the checklist and, if needed, the handoff prompt instead.

## Mandatory first output

Before doing anything else, print this exact line so the user knows the skill is active:

```text
[phase-review] Skill active. Running phase gate-check...
```

## Step 1 — Identify the phase

Extract the target phase number from what the user said.

If no phase number was given, default to the **current phase**: the lowest phase number that has any work items still in `work_items/ready/` (i.e. `WI-N.*` files present in that directory).

Tell the user which phase was selected before continuing.

## Step 2 — Read phase artefacts

Collect the following files. Skip archived files (any path containing `/archive/` or `.archived.`).

| Artefact | Where to find it |
|----------|-----------------|
| Phase PRD | Under `docs/prds/`, open the phase directory for your target (e.g. `docs/prds/phase-2/` when reviewing phase 2) and read all non-archived `.md` files there |
| Done WIs for this phase | `work_items/done/` — all files matching prefix `WI-N.` where N is the phase number |
| Ready WIs for this phase | `work_items/ready/` — all files matching prefix `WI-N.` |
| Public API surface | `src/modules/risk_analytics/__init__.py` (or the relevant module `__init__.py` identified in the PRD) |
| Phase completion criteria | `docs/roadmap/phased_implementation_roadmap.md` |

## Step 3 — Evaluate and print checklist

Tick each item as `pass`, `fail`, or `partial`. Use this exact format:

```text
--- Phase N Gate-Check ---
[ ] All phase WIs in done/          : <pass | N remaining: list IDs>
[ ] PRD public API surface exported : <pass | missing: list symbols>
[ ] Replay fixtures present         : <pass | missing>
[ ] ADR gaps identified             : <none | list>
[ ] Open PRD questions              : <none | list>
[ ] Drift monitor run since last WI : <yes | no — suggest run-drift if no>
--- Verdict: GO | NO-GO ---
```

Evaluation rules:

- **All phase WIs in done/**: count `WI-N.*` files in `work_items/ready/`. Pass if count is zero.
- **PRD public API surface exported**: extract `__all__` or exported symbols from the PRD contract section. Compare against what is actually exported in the module `__init__.py`. Pass if every symbol listed in the PRD is present.
- **Replay fixtures present**: check `fixtures/` for at least one fixture file referencing phase-N work (by name convention or PRD-listed fixture paths). Pass if found.
- **ADR gaps identified**: scan the PRD for any open ADR references or deferred architecture decisions. Pass (none) if the PRD has no unresolved ADR stubs.
- **Open PRD questions**: check the PRD for an "Open Questions" section. Pass (none) if the section is absent or explicitly lists "none".
- **Drift monitor run since last WI**: check `artifacts/drift/` for a report dated after the most recent WI merge (use file modification time heuristic if git log is unavailable). If uncertain, mark `no` and suggest running `python scripts/drift/run_all.py`.

## Step 4 — If GO

Print one sentence confirming the phase is complete, then tell the user:

```text
Phase N is complete. Run the `new-prd` skill to begin planning phase N+1.
```

## Step 5 — If NO-GO

Fill `prompts/agents/invocation_templates/pm_invocation.md` and print one fenced handoff block routing the PM agent to address the gaps found.

Replace the placeholders as follows:

- `<LINKED_PRD>` → path to the phase PRD file
- `<TARGET_WORK_ITEM>` → path to the first remaining ready WI, or `(none — all WIs done)` if the gaps are only about exports or fixtures
- `<LINKED_ADRS>` → ADR paths found in the PRD dependencies section
- `<CONTEXT — what has changed since the last assessment, recent merges, known blockers>` → `"Phase N gate-check found the following gaps: [paste the failing checklist lines]."`
- `<TASK — e.g. "Reassess whether WI-X.Y.Z is now coding-ready on merged main.">` → `"Triage each gap. For WIs not yet in done/, assess what is blocking them. For missing API exports or fixtures, create or update work items. For ADR gaps, route to the PRD/Spec Author."`

Then print:

```text
Paste this into a FRESH PM Agent session (new chat / new Codex session):
Recommended model: Sonnet (or equivalent mid-tier)

[complete filled pm_invocation.md content]
```

## Hard stops

- STOP if you are about to edit any file.
- STOP if you are about to create a work item yourself.
- STOP if you are about to implement or fix any gap you found.
- In all of these cases: report the finding in the checklist and, if NO-GO, produce the filled PM invocation prompt instead.

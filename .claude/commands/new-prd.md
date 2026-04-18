---
name: new-prd
description: Produces a filled PRD/Spec Author invocation prompt when the user says things like "new PRD", "spec a new capability", "write a PRD for X", or "start phase 2". Never writes a PRD itself — only builds the copy-paste prompt for the PRD/Spec Author agent.
---
<!-- GENERATED SKILL MIRROR: do not edit directly -->


# new-prd

> **HARD CONSTRAINT — read this before anything else.**
>
> This skill NEVER writes a PRD, never edits any doc file, and never authors spec content itself.
> Its only job is to collect context and produce a filled, copy-paste-ready invocation prompt for the PRD/Spec Author agent.
> The user pastes that prompt into a **separate** fresh agent session to do the actual PRD authoring.
> If you feel tempted to start writing the PRD — stop. Produce the prompt instead.

## Mandatory first output

Before doing anything else, print this exact line so the user knows the skill is active:

```text
[new-prd] Skill active. Building PRD/Spec Author prompt...
```

## Step 1 — Identify the capability

Extract the capability name from what the user said.

- If the user said something like "write a PRD for X" or "spec X", use X as the capability name.
- If the capability name is unclear, ask **one** clarifying question and wait for the answer before continuing.

## Step 2 — Determine the PRD ID

List `docs/prds/` (all subdirectories and files) to find the highest existing PRD number.

- If the highest existing PRD is in a `phase-N/` folder, the next new PRD is `PRD-(N+1).1` in a new `phase-(N+1)/` folder — unless the user explicitly said "phase N" or the roadmap indicates remaining work in the current phase.
- If the user said "start phase 2" or a specific phase number, use that phase.
- Propose the next PRD ID (e.g. `PRD-2.1`) and the target folder (e.g. `docs/prds/phase-2/`) as part of the prompt context.

## Step 3 — Read context files

Read the following files and extract the relevant context to fill the prompt:

- `docs/roadmap/phased_implementation_roadmap.md` — extract the one-liner phase context for the proposed phase.
- All files under `docs/adr/` — list their paths; these will be passed as `<LINKED_ADRS>`.
- The most recent PRD file found in step 2 — this is the reference exemplar.

## Step 4 — Check for an existing phase kickoff template

Check whether `prompts/agents/invocation_templates/phase2_prd_kickoff.md` exists.

- If it exists **and** the requested phase matches (e.g. user said "phase 2" or the proposed PRD ID is PRD-2.x), use `phase2_prd_kickoff.md` as the template instead of `prd_spec_invocation.md`.
- Print a note telling the operator which template was selected, for example:

```text
Note: using phase2_prd_kickoff.md (phase 2 match detected).
```

or

```text
Note: using prd_spec_invocation.md (generic — no phase-specific template matched).
```

## Step 5 — Fill the selected template

Using the template selected in step 4, replace every placeholder as follows.

Use `prompts/agents/invocation_templates/prd_spec_invocation.md` as the default template.
Replace the **exact bracketed placeholder string as written in the template** — including any descriptive suffix.

| Placeholder | Value |
|---|---|
| `<LINKED_ADRS>` | Paths of all ADR files found in step 3 (one per line) |
| `<EXISTING_PRD_IF_UPDATING>` | Path to the most recent PRD found in step 2 (as reference exemplar, not being updated) |
| `<RELEVANT_WORK_ITEMS>` | `none (new PRD)` |
| `<RELEVANT_SOURCE_FILES>` | `none` unless the user specified source files |
| `<CONTEXT>` | `Authoring [PRD-ID] for capability: [capability name]. Phase context: [one-liner from roadmap].` |
| `<TASK>` | `Write a bounded, implementation-ready PRD for [capability name] following the PRD-1.1-v2 structure as exemplar.` |
| `<NUMBERED_LIST>` | Standard required outcomes (see below) |
| `<ADDITIONAL_CONSTRAINTS>` | `Do not redesign Phase 1 contracts.` |
| `<FOCUS_AREAS>` | `API surface, error semantics, reuse of shared infrastructure, issue decomposition guidance` |
| `<EXPECTED_RESULT>` | `A new docs/prds/phase-N/[PRD-ID]-[capability-name].md ready for Issue Planner decomposition` |

Standard required outcomes for `<NUMBERED_LIST>`:

1. Capability area identified and justified
2. Typed contracts defined
3. Error and degraded-case semantics explicit
4. Reuse of Phase 1 infrastructure identified
5. ADR gaps identified
6. Issue decomposition guidance provided

## Step 6 — Print the filled prompt

Print exactly one fenced block. The first two lines are always the session header and the recommended model:

```text
Paste this into a FRESH PRD/Spec Author agent session (new chat / new Codex session):
Recommended model: Sonnet (consider bumping to Opus / GPT-5.4 for methodology-heavy specs)

[complete filled invocation template content]
```

The user opens a new chat, selects the recommended model, then pastes the whole block. Do not act on it.

## Step 7 — Add the freshness reminder

After the prompt block, always print:

```text
Before the agent starts:
  git fetch origin && git switch main && git pull --ff-only origin main
For PRD authoring: work from a fresh branch created from main.
```

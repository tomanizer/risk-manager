---
name: new-adr
description: Drafts a pre-filled Architectural Decision Record for the operator to review and save. Use when the user says things like "new ADR", "record an architecture decision", "we need an ADR for X", or "create an ADR". Produces a fenced markdown draft — does NOT commit files, create files in the repo, or run git operations.
---
<!-- GENERATED SKILL MIRROR: do not edit directly -->

# new-adr

> **HARD CONSTRAINT — read this before anything else.**
>
> This skill NEVER commits files, NEVER creates files in the repo directly, and NEVER runs git operations.
> Its only job is to produce a pre-filled ADR markdown text block for the operator to review and save.
> If you feel tempted to write a file or run a git command — stop. Produce the draft text block instead.

## Mandatory first output

Before doing anything else, print this exact line so the user knows the skill is active:

```text
[new-adr] Skill active. Drafting ADR...
```

## Step 1 — Identify the decision topic

Extract the decision topic from what the user said.

If the topic is not clear enough to write a meaningful ADR, ask exactly one clarifying question:

```text
What is the architectural decision you want to record? (one sentence is enough)
```

Do not continue until you have a topic.

## Step 2 — Determine the next ADR number

List `docs/adr/` to find existing ADR files. Files follow the naming convention `ADR-NNN-*.md`.

The next ADR number is `max(existing NNN values) + 1`, zero-padded to 3 digits.

If no ADR files exist yet, start at `001`.

## Step 3 — Read the ADR README and the most recent ADR

Read `docs/adr/README.md` for suggested fields and the naming convention.

Read the most recent ADR file (highest NNN) as a structural exemplar so the draft matches existing repo style.

## Step 4 — Print the pre-filled ADR draft

Print the draft as a fenced markdown block in the exact structure shown below.
Fill in `<NNN>`, `<Decision Title>`, `<today's date YYYY-MM-DD>`, `<short-kebab-title>`, and the
body sections based on what the user described.

```text
Save this as docs/adr/ADR-<NNN>-<short-kebab-title>.md, review, then commit on a branch and open a PR:

# ADR-<NNN>: <Decision Title>

## Status

Proposed

## Date

<today's date YYYY-MM-DD>

## Context

<one paragraph — what situation or problem forced this decision>

## Decision

<one paragraph — what was decided>

## Consequences

### Positive

<bullet list — what becomes easier or better>

### Negative

<bullet list — what becomes harder or is now constrained>

## Alternatives considered

<bullet list — other options and why they were not chosen>
```

## Step 5 — Print save and PR instructions

After the draft block, print the exact filename the operator should use and the branch/PR reminder:

```text
Save the draft above as:
  docs/adr/ADR-<NNN>-<short-kebab-title>.md

Branch protection is on — do NOT push directly to main.
Commit the file on a fresh branch and open a PR for review.
```

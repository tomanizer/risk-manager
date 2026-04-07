# Cursor Skills

This directory contains Cursor skills for the `risk-manager` repository.

## Available skills

| Skill | Trigger phrases | Description |
|-------|----------------|-------------|
| [deliver-wi](deliver-wi/SKILL.md) | "work on WI", "implement WI-X", "what should I do next", "run PM agent" | Drives delivery of a work item through the PM → Coding → Review relay. Produces a filled invocation prompt — never implements directly. |
| [new-adr](new-adr/SKILL.md) | "new ADR", "record an architecture decision", "we need an ADR for X", "create an ADR" | Drafts a pre-filled ADR for operator review and save; does not commit files or run git operations. |
| [new-prd](new-prd/SKILL.md) | "new PRD", "spec a new capability", "write a PRD for X", "start phase 2" | Produces a filled PRD/Spec Author invocation prompt; does not author PRD content directly. |
| [phase-review](phase-review/SKILL.md) | "phase review", "is this phase done", "check phase completion" | Assesses phase completion against acceptance criteria and identifies remaining gaps. |
| [repo-status](repo-status/SKILL.md) | "repo status", "what's the status", "morning check", "what's in progress" | Prints a read-only situational awareness dashboard: phase, WI counts, open PRs, CI summary, and suggested next action. |
| [run-drift](run-drift/SKILL.md) | "run drift", "audit the repo", "check repo health", "run the drift monitor" | Produces a filled Drift Monitor invocation prompt; does not execute drift audits directly. |

## Skill structure

Each skill lives in its own subdirectory and follows the same pattern:

- YAML frontmatter (`name:`, `description:`)
- A `HARD CONSTRAINT` block at the top
- A mandatory first output line
- Numbered steps
- Fenced output blocks with language tags

The skills are also copied to `~/.cursor/skills/<skill-name>/SKILL.md` so they are available globally from any Cursor workspace.

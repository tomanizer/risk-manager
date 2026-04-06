# Cursor Skills

This directory contains Cursor skills for the `risk-manager` repository.

## Available skills

| Skill | Trigger phrases | Description |
|-------|----------------|-------------|
| [deliver-wi](deliver-wi/SKILL.md) | "work on WI", "implement WI-X", "what should I do next", "run PM agent" | Drives delivery of a work item through the PM → Coding → Review relay. Produces a filled invocation prompt — never implements directly. |
| [repo-status](repo-status/SKILL.md) | "repo status", "what's the status", "morning check", "what's in progress" | Prints a read-only situational awareness dashboard: phase, WI counts, open PRs, CI summary, and suggested next action. |

## Skill structure

Each skill lives in its own subdirectory and follows the same pattern:

- YAML frontmatter (`name:`, `description:`)
- A `HARD CONSTRAINT` block at the top
- A mandatory first output line
- Numbered steps
- Fenced output blocks with language tags

The skills are also copied to `~/.cursor/skills/<skill-name>/SKILL.md` so they are available globally from any Cursor workspace.

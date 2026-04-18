# Skills

This directory is the canonical source of truth for repository skills.

Edit only `skills/<name>/SKILL.md`, then run `python scripts/skills/sync_skill_mirrors.py`.

## Available skills

| Skill | Claude command | Description |
| --- | --- | --- |
| [babysit](babysit/SKILL.md) | `/babysit` | Keep a GitHub PR merge-ready: triage review comments, resolve inline threads, fix merge conflicts when intent is clear, and repair merge-blocking CI with small scoped commits until checks are green. Tool-agnostic — use in Cursor, Claude Code, Codex, Copilot, or any agent that can run git and gh. |
| [deliver-wi](deliver-wi/SKILL.md) | `/deliver-wi` | Drives delivery of a risk-manager work item through the PM → Coding → Review relay. Use when the user wants to work on a work item, implement a WI, run the PM agent, invoke the coding agent, invoke the review agent, advance a work item, or asks what to do next. Produces a filled invocation prompt for the correct specialist agent — does NOT implement anything itself. |
| [new-adr](new-adr/SKILL.md) | `/new-adr` | Drafts a pre-filled Architectural Decision Record for the operator to review and save. Use when the user says things like "new ADR", "record an architecture decision", "we need an ADR for X", or "create an ADR". Produces a fenced markdown draft — does NOT commit files, create files in the repo, or run git operations. |
| [new-prd](new-prd/SKILL.md) | `/new-prd` | Produces a filled PRD/Spec Author invocation prompt when the user says things like "new PRD", "spec a new capability", "write a PRD for X", or "start phase 2". Never writes a PRD itself — only builds the copy-paste prompt for the PRD/Spec Author agent. |
| [phase-review](phase-review/SKILL.md) | `/phase-review` | Produces a go/no-go gate-check checklist for a delivery phase. Use when the user says "phase review", "check if phase N is done", "are we ready for phase N+1", or "review the phase". Reads and reports only — never edits files or creates work items. |
| [repo-status](repo-status/SKILL.md) | `/repo-status` | Prints a structured, read-only situational awareness dashboard. Use when the user says things like "repo status", "what's the status", "morning check", "what's in progress", or "what should I work on". |
| [run-drift](run-drift/SKILL.md) | `/run-drift` | Produces a filled Drift Monitor invocation prompt when the user says things like "run drift", "audit the repo", "check repo health", or "run the drift monitor". Does NOT run the audit itself. |

## Generated mirrors

| Location | Purpose |
| --- | --- |
| `.cursor/skills/<name>/SKILL.md` | Cursor-native skill discovery |
| `.claude/commands/<name>.md` | Claude Code slash commands |
| `.github/skills/<name>/SKILL.md` | GitHub / Copilot / VSCode discovery |

## Maintenance

After editing a canonical skill:

```bash
python scripts/skills/sync_skill_mirrors.py
python scripts/skills/check_skill_mirrors.py
```

Generated mirrors are tracked in git so every supported platform can discover the same skill content without relying on symlinks.

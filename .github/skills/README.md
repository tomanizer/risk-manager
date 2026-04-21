# Skills (generated mirrors)

Each `*/SKILL.md` here is a generated mirror of the canonical file under `skills/<name>/SKILL.md`.

Do not edit files here by hand.

## Available skills

| Skill | Mirror path | Description |
| --- | --- | --- |
| `babysit` | `.github/skills/babysit/SKILL.md` | Keep a GitHub PR merge-ready: triage review comments, resolve inline threads, wait for draft-stage Gemini feedback, promote the PR when ready, verify the Copilot review pass, fix merge conflicts when intent is clear, and repair merge-blocking CI with small scoped commits until checks are green. Tool-agnostic — use in Cursor, Claude Code, Codex, Copilot, or any agent that can run git and gh. |
| `deliver-wi` | `.github/skills/deliver-wi/SKILL.md` | Drives delivery of a risk-manager work item through the PM → Coding → Review relay. Use when the user wants to work on a work item, implement a WI, run the PM agent, invoke the coding agent, invoke the review agent, advance a work item, or asks what to do next. Produces a filled invocation prompt for the correct specialist agent — does NOT implement anything itself. |
| `new-adr` | `.github/skills/new-adr/SKILL.md` | Drafts a pre-filled Architectural Decision Record for the operator to review and save. Use when the user says things like "new ADR", "record an architecture decision", "we need an ADR for X", or "create an ADR". Produces a fenced markdown draft — does NOT commit files, create files in the repo, or run git operations. |
| `new-prd` | `.github/skills/new-prd/SKILL.md` | Produces a filled PRD/Spec Author invocation prompt when the user says things like "new PRD", "spec a new capability", "write a PRD for X", or "start phase 2". Never writes a PRD itself — only builds the copy-paste prompt for the PRD/Spec Author agent. |
| `phase-review` | `.github/skills/phase-review/SKILL.md` | Produces a go/no-go gate-check checklist for a delivery phase. Use when the user says "phase review", "check if phase N is done", "are we ready for phase N+1", or "review the phase". Reads and reports only — never edits files or creates work items. |
| `repo-status` | `.github/skills/repo-status/SKILL.md` | Prints a structured, read-only situational awareness dashboard. Use when the user says things like "repo status", "what's the status", "morning check", "what's in progress", or "what should I work on". |
| `run-drift` | `.github/skills/run-drift/SKILL.md` | Produces a filled Drift Monitor invocation prompt when the user says things like "run drift", "audit the repo", "check repo health", or "run the drift monitor". Does NOT run the audit itself. |

## Maintenance

```bash
python scripts/skills/sync_skill_mirrors.py
python scripts/skills/check_skill_mirrors.py
```

See also `skills/README.md` and `.cursor/skills/README.md`.

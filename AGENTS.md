# AGENTS.md

This repository uses AI agents for PRD authoring, issue decomposition, implementation, review, project coordination, and repo-wide drift monitoring.

## Architecture hierarchy
1. `docs/` contains the governed architecture canon.
2. `docs/delivery/`, `docs/methodology/`, `docs/engineering/`, and `docs/shared_infra/` contain governed operating, domain, and implementation canon for specialist agents.
3. `docs/prds/` and `docs/prd_exemplars/` define implementation contracts and exemplars.
4. `prompts/` contains AI-mediated delivery instructions.
5. `work_items/` holds bounded execution slices.
6. `src/` contains implementation.
7. `tests/` and `fixtures/` verify correctness and replayability.

## Agent roles

Each role has a detailed instruction file in `prompts/agents/` and a Copilot agent profile in `.github/agents/`. The legacy Risk Methodology Spec Agent (`risk-methodology-spec.agent.md`) is retained for backward compatibility but its responsibilities are now covered by the PRD / Spec Author.

### PRD / Spec Author
- writes bounded implementation-ready PRDs and methodology-aware specifications
- makes typed contracts, status models, error semantics, and degraded cases explicit
- applies methodology-aware judgment when the capability involves market-risk concepts
- keeps scope narrow and makes ambiguities explicit in Open Questions
- does not push contract or status-semantic decisions to coding
- instruction: `prompts/agents/prd_spec_agent_instruction.md`

### Coding Agent
- implements one bounded work item at a time
- stays within linked PRD and issue scope
- preserves architecture boundaries
- includes tests and required evidence/logging hooks
- prefers direct, readable, low-abstraction implementations
- prefers established performance-oriented libraries and vectorized execution where appropriate
- instruction: `prompts/agents/coding_agent_instruction.md`

### Review Agent
- reviews against PRD and issue, not personal style preference
- checks contract fidelity, boundary discipline, degraded-case handling, evidence, replayability, and tests
- flags scope creep explicitly
- instruction: `prompts/agents/review_agent_instruction.md`

### PM / Coordination Agent
- manages sequencing, dependency readiness, blockers, and milestone integrity
- does not redesign architecture during execution
- prefers the narrowest reviewable slice that preserves momentum
- routes canon gaps back to spec work rather than asking coding to improvise
- instruction: `prompts/agents/pm_agent_instruction.md`

### Issue Planner Agent
- turns approved PRDs into small, testable, implementation-ready work items
- preserves dependency order and architecture boundaries
- makes acceptance criteria explicit and reviewable
- instruction: `prompts/agents/issue_planner_instruction.md`

### Drift Monitor Agent
- audits repo-wide coherence across canon, prompts, work items, registry, implementation, and tests
- detects contradictory, duplicated, stale, sprawling, or weakly governed content
- distinguishes sanctioned duplication from conflicting duplication
- reports design drift, technical boundary erosion, and source-of-truth ambiguity with evidence
- routes findings to PM, PRD, methodology/spec, coding, review, repository maintenance, or human decision
- does not silently rewrite canon, approve merge readiness, or widen implementation scope on its own
- instruction: `prompts/agents/drift_monitor_agent_instruction.md`

## Role separation rule

The repository uses a gated relay, not a single do-everything agent.

The intended handoff is:
1. PM / Coordination Agent
2. PRD / Spec Author or Issue Planner when needed
3. Coding Agent
4. Review Agent
5. Human merge decision

Do not collapse planning, coding, review, and merge judgment into one agent pass when operating autonomously.

Repo-wide drift monitoring is a separate periodic governance control. It does not replace the PM -> coding -> review delivery relay for implementation work.

For a comprehensive guide to the agent framework — what the agents are, how they work, how to use them manually and autonomously across tools — see `docs/guides/agent_framework.md`.

Repo-visible role-specific instructions live in:
- `prompts/agents/` — canonical standing instructions and invocation templates
- `docs/guides/agent_framework.md` — framework overview and tool-specific setup
- `docs/guides/overnight_agent_runbook.md` — operational runbook
- `docs/guides/agent_workflow_guide.md` — tool-specific usage patterns
- `docs/delivery/` — PM and delivery canon
- `docs/methodology/` — risk methodology canon
- `docs/engineering/` — coding and engineering canon
- `docs/shared_infra/` — shared infrastructure canon and adoption matrix
- `docs/guides/repo_health_audit_checklist.md` — drift monitor checklist

## Agent skills

<!-- BEGIN GENERATED SKILLS SECTION -->

Reusable agent skills are defined in `skills/` and generated into `.cursor/skills/`, `.claude/commands/`, and `.github/skills/` for platform-native discovery. Edit only `skills/<name>/SKILL.md`, then run `python scripts/skills/sync_skill_mirrors.py`. Most skills produce a filled invocation prompt for the correct specialist agent and **do not implement work themselves**. The **`babysit`** skill is the exception: it may run `git` / `gh`, triage threads, and push **small merge-readiness** commits per `skills/babysit/SKILL.md`.

Available skills:

| Skill | Invoke in Claude Code | Purpose |
| --- | --- | --- |
| `babysit` | `/babysit` | Keep a GitHub PR merge-ready: triage review comments, resolve inline threads, wait for draft-stage Gemini feedback, promote the PR when ready, verify the Copilot review pass, fix merge conflicts when intent is clear, and repair merge-blocking CI with small scoped commits until checks are green. Tool-agnostic — use in Cursor, Claude Code, Codex, Copilot, or any agent that can run git and gh. |
| `deliver-wi` | `/deliver-wi` | Drives delivery of a risk-manager work item through the PM → Coding → Review relay. Use when the user wants to work on a work item, implement a WI, run the PM agent, invoke the coding agent, invoke the review agent, advance a work item, or asks what to do next. Produces a filled invocation prompt for the correct specialist agent — does NOT implement anything itself. |
| `new-adr` | `/new-adr` | Drafts a pre-filled Architectural Decision Record for the operator to review and save. Use when the user says things like "new ADR", "record an architecture decision", "we need an ADR for X", or "create an ADR". Produces a fenced markdown draft — does NOT commit files, create files in the repo, or run git operations. |
| `new-prd` | `/new-prd` | Produces a filled PRD/Spec Author invocation prompt when the user says things like "new PRD", "spec a new capability", "write a PRD for X", or "start phase 2". Never writes a PRD itself — only builds the copy-paste prompt for the PRD/Spec Author agent. |
| `phase-review` | `/phase-review` | Produces a go/no-go gate-check checklist for a delivery phase. Use when the user says "phase review", "check if phase N is done", "are we ready for phase N+1", or "review the phase". Reads and reports only — never edits files or creates work items. |
| `repo-status` | `/repo-status` | Prints a structured, read-only situational awareness dashboard. Use when the user says things like "repo status", "what's the status", "morning check", "what's in progress", or "what should I work on". |
| `run-drift` | `/run-drift` | Produces a filled Drift Monitor invocation prompt when the user says things like "run drift", "audit the repo", "check repo health", or "run the drift monitor". Does NOT run the audit itself. |

In Cursor, invoke by name in chat using the generated mirrors under `.cursor/skills/`. In Claude Code, use the `/skill-name` slash command from `.claude/commands/<skill>.md`. GitHub-oriented discovery can use `.github/skills/<skill>/SKILL.md`. In Codex, Copilot, VSCode, and other environments, point the agent at `skills/<skill>/SKILL.md` or reference the skill by name in your prompt.

<!-- END GENERATED SKILLS SECTION -->
## Freshness and branching rule

Refresh the control checkout before any PM, coding, review, or drift-monitor pass:

1. git fetch origin
2. git switch main
3. git pull --ff-only origin main

Then follow one of these two modes only:

### Manual direct mode

- use this only when a human is invoking an agent outside `agent_runtime`
- PM, spec, issue-planner, coding, and drift-monitor work start from the refreshed control checkout
- new implementation work must start from the latest `main`
- each bounded implementation slice should use a fresh feature branch created from current `main`
- review work should inspect the PR head in an isolated checkout rather than reusing unrelated local state

### Runtime-managed mode

- `agent_runtime` is the authority for execution checkout state
- the control checkout stays on refreshed `main` and is used only for dispatch, inspection, and human repo maintenance
- the real PM, spec, issue-planner, coding, review, and drift-monitor work happens only in the runtime-allocated worktree for that run
- agents must not run `git switch main`, `git worktree add`, or create a second feature branch inside a runtime-managed session
- new coding work without an existing PR starts from a runtime-created worktree based on current `origin/main`
- review and PR-follow-up coding work use the runtime-managed checkout for the PR head lineage, not a second branch from local `main`
- when the runtime provides a detached PR-head checkout, agents must keep working in that checkout and use the provided PR head push target rather than creating a local branch

Agents must not continue from stale local state when canon, PR state, or linked contracts may have changed.

## Non-negotiable repository rules
- deterministic services own calculations and canonical state
- walkers interpret typed outputs only
- orchestrators execute workflow state, routing, gates, and handoff only
- UI must not hide caveats or recompute canonical logic
- trust before interpretation
- challenge before governance output
- evidence and replayability are first-class requirements

## Preferred behavior
- choose the narrower implementation when ambiguous
- preserve explicit caveats rather than guessing
- prefer small, reviewable changes over broad refactors
- keep generated prose precise and low-fluff

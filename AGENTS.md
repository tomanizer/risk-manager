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

Reusable agent skills are defined in `.cursor/skills/` and mirrored as Claude Code slash commands in `.claude/commands/`. Most skills produce a filled invocation prompt for the correct specialist agent and **do not implement work themselves**. The **`babysit`** skill is the exception: it may run `git` / `gh`, triage threads, and push **small merge-readiness** commits per `.cursor/skills/babysit/SKILL.md`.

Available skills:

| Skill | Invoke in Claude Code | Purpose |
| --- | --- | --- |
| `deliver-wi` | `/deliver-wi` | Identify next work item and produce agent handoff prompt |
| `phase-review` | `/phase-review` | Assess phase completion against acceptance criteria |
| `repo-status` | `/repo-status` | Situational awareness dashboard |
| `run-drift` | `/run-drift` | Trigger a drift monitor pass |
| `new-prd` | `/new-prd` | Scaffold a new PRD |
| `babysit` | `/babysit` | Keep a PR merge-ready (CI, threads, conflicts); see `.cursor/skills/babysit/SKILL.md` |

In Cursor, invoke by name in chat. In Claude Code, use the `/skill-name` slash command: `.claude/commands/<skill>.md` symlinks to `.cursor/skills/<skill>/SKILL.md`. GitHub-oriented discovery can use `.github/skills/<skill>/SKILL.md` (same symlink). In other environments (Codex, Copilot), point the agent at `.cursor/skills/<skill>/SKILL.md` or reference the skill by name in your prompt.

## Freshness and branching rule

Before any PM, coding, review, or drift-monitor pass:

1. git fetch origin
2. git switch main
3. git pull --ff-only origin main

For reviews, then checkout the latest PR head. For coding, create a fresh branch from main.

New implementation work must start from the latest `main`.

Each bounded implementation slice should use a fresh branch created from current `main`.

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

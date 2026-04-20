# Agent Framework

## What this is

This repository uses a structured multi-agent framework to manage its entire software delivery lifecycle: specification, planning, implementation, review, and ongoing governance. Instead of one all-purpose AI coding assistant, the work is split across six specialized agent roles that hand off to each other in a governed relay.

The framework is tool-agnostic. The same roles, instructions, and invocation patterns work across Claude Code, OpenAI Codex, Cursor, VS Code with Copilot, and GitHub Copilot coding agent. The agent definitions live in the repository itself, so every tool reads the same source of truth.

## Why a multi-agent relay

A single agent session that plans, codes, reviews, and merges its own work has no governance boundary. It can silently widen scope, invent contracts, drift from the approved design, and approve its own mistakes.

The relay model prevents this by enforcing role separation:

- The PM agent decides *what* to build next, but cannot write code.
- The coding agent implements *exactly one slice*, but cannot approve its own PR.
- The review agent checks the result against approved artifacts, but cannot rewrite the implementation.
- The human retains merge authority.

Each agent reads from the same governed artifacts (PRDs, ADRs, work items) and is constrained by explicit scope, stop conditions, and forbidden behaviors. The relay is intentionally slower than a single agent doing everything, but it catches the errors that matter.

## The six agent roles

### PM / Coordination Agent

Owns backlog sequencing, dependency readiness, blocker identification, and implementation briefs. The PM agent decides whether a work item is ready for coding, and if so, produces a bounded brief that tells the coding agent exactly what to build, where to build it, and when to stop.

**When to use:** before any coding work, when triaging review feedback, when deciding what to build next.

### PRD / Spec Author Agent

Writes bounded, implementation-ready PRDs and methodology-aware specifications. Makes typed contracts, status models, error semantics, and degraded cases explicit so that downstream agents do not need to invent them. When the capability involves market-risk methodology, applies domain-specific judgment to ensure precision.

**When to use:** when a new capability needs a PRD, when an existing PRD has a gap or ambiguity that blocks coding, when methodology concepts need precise definition before implementation.

### Issue Planner Agent

Turns broad PRDs into small, testable, implementation-ready work items with explicit dependencies, target areas, and acceptance criteria. Produces the bounded slices that the PM agent evaluates for readiness and the coding agent implements.

**When to use:** when a PRD is too large for a single coding pass, when the PM agent identifies that a work item needs splitting, when a blocker requires a prerequisite work item.

### Coding Agent

Implements exactly one bounded work item at a time. Stays within the approved scope, preserves architecture boundaries, adds tests, and opens a draft PR. Does not invent contracts, status semantics, or architecture decisions that should have been resolved in a PRD or ADR.

**When to use:** when a work item is marked ready by the PM agent, with a bounded implementation brief, explicit target area, and clear stop conditions.

### Review Agent

Reviews delivered changes against the linked work item, PRD, ADRs, and changed files. Checks scope fidelity, contract correctness, degraded-case handling, replay safety, boundary discipline, and test sufficiency. Triages external bot comments (Gemini, Copilot) as valid, partial, or not applicable.

**When to use:** after the coding agent opens a draft PR, before any merge decision.

### Drift Monitor Agent

Audits repository-wide coherence across canon documents, prompts, work items, registry state, implementation, and tests. Detects contradictions, stale guidance, boundary erosion, and document sprawl. Routes findings to the correct owner rather than silently rewriting anything.

**When to use:** on a separate cadence from delivery work, as a periodic governance control. Not as a replacement for PR review.

## How the relay works

### Delivery relay (per work item)

```text
PM Agent                     decides what to build, produces implementation brief
    │
    ├── if PRD gap ──────►   PRD / Spec Author    fills the gap, returns to PM
    ├── if too broad ────►   Issue Planner         splits into smaller items, returns to PM
    │
    ▼
Coding Agent                 implements one slice, opens draft PR
    │
    ▼
Review Agent                 reviews PR against approved artifacts
    │
    ▼
Human                        merge / reject / send back
```

### Repo-health loop (separate cadence)

```text
Drift Monitor Agent          audits repo-wide coherence on current main
    │
    ▼
PM Agent or Human            triages findings into PM / PRD / coding / review / human queues
```

These two loops run independently. The drift monitor does not replace PR review, and the delivery relay does not replace periodic governance audits.

## Repository structure

All agent definitions follow a layered architecture with one canonical source of truth per role:

### Standing instructions (canonical source of truth)

```text
prompts/agents/
├── pm_agent_instruction.md
├── prd_spec_agent_instruction.md
├── issue_planner_instruction.md
├── coding_agent_instruction.md
├── review_agent_instruction.md
├── drift_monitor_agent_instruction.md
└── risk_methodology_spec_agent_instruction.md   (legacy, folded into prd_spec)
```

Each instruction file defines the role's mission, required reading order, primary responsibilities, operating rules, stop conditions, and forbidden behavior. These are the single source of truth for how each agent should behave.

### Invocation templates (per-task prompts)

```text
prompts/agents/invocation_templates/
├── pm_invocation.md
├── prd_spec_invocation.md
├── issue_planner_invocation.md
├── coding_invocation.md
├── review_invocation.md
└── drift_monitor_invocation.md
```

These are fill-in-the-blanks templates that bridge standing instructions to specific tasks. Copy one, fill in the placeholders (work item, PRD, context, scope, stop conditions), and paste it as the prompt to your agent. The invocation template tells the agent to read its standing instruction file first, then apply the task-specific context.

### Tool-specific surfaces (thin pointers)

```text
AGENTS.md                                    master role definitions, links to instruction files
CLAUDE.md                                    Claude Code / Cursor routing
GEMINI.md                                    Gemini routing
.github/agents/*.agent.md                    GitHub Copilot custom agent profiles
.github/copilot-instructions.md              Copilot repository-wide instructions
.github/instructions/*.instructions.md       Copilot path-scoped instructions
```

These files are intentionally thin. They identify the role, point to the canonical instruction file, and add only tool-specific behavior (such as git freshness rules or output format). They do not duplicate the full operating rules.

### Supporting documentation

```text
docs/guides/overnight_agent_runbook.md       operational runbook for the delivery relay
docs/guides/agent_workflow_guide.md          tool-specific usage patterns
agent_runtime/                               automated delivery orchestration (semi-autonomous)
```

## How to use the agents

### Quick start: manual invocation

The simplest way to use the agents is to copy an invocation template, fill in the placeholders, and paste it into your tool of choice.

#### Example: ask the PM agent whether a work item is ready

1. Open `prompts/agents/invocation_templates/pm_invocation.md`
2. Fill in:
   - `<LINKED_PRD>` with the path to the relevant PRD
   - `<TARGET_WORK_ITEM>` with the path to the work item
   - `<LINKED_ADRS>` with paths to relevant ADRs
   - `<CONTEXT>` with what has changed recently
   - `<TASK>` with "Reassess whether WI-X.Y.Z is coding-ready"
3. Paste the filled template into Claude Code, Codex, Cursor, or any other agent surface
4. The agent reads `AGENTS.md` and `prompts/agents/pm_agent_instruction.md` first, then applies the task context
5. It returns `READY` with an implementation brief, `BLOCKED` with exact reasons, or `SPLIT_REQUIRED` with proposed narrower items

#### Example: implement a coding slice

1. Get the implementation brief from the PM agent (previous step)
2. Open `prompts/agents/invocation_templates/coding_invocation.md`
3. Fill in the scope, target area, out-of-scope, acceptance targets, and stop conditions from the PM brief
4. Paste into a fresh agent session
5. The coding agent creates a branch, implements the slice, adds tests, and opens a draft PR

#### Example: review a PR

1. Open `prompts/agents/invocation_templates/review_invocation.md`
2. Fill in the PR number, linked work item, PRD, and ADRs
3. Paste into a fresh agent session
4. The review agent returns pass/fail with material findings, missing tests, and required changes

### The freshness rule

Before any agent pass, sync to the latest `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

For reviews, then checkout the PR head. For coding, create a fresh branch from `main`. Agents must not work from stale local state.

## Local environment setup

Before using any tool with this repository, configure your local environment
with the API keys for the providers you plan to use.

### 1. Copy the environment template

```bash
cp .env.example .env
```

`.env` is gitignored and must never be committed. `.env.example` documents
every available variable and is the committed source of truth for the
configuration schema.

### 2. Fill in your API keys

Open `.env` and uncomment the keys for the providers you want to use.
All keys are optional; the runtime and agents skip providers that have no
key set.

| Provider | Variable | Where to get it |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic / Claude | `ANTHROPIC_API_KEY` | [console.anthropic.com/keys](https://console.anthropic.com/keys) |
| Google Gemini | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| Cursor | `CURSOR_API_KEY` | Cursor account settings |
| LangSmith (tracing) | `LANGCHAIN_API_KEY` | [smith.langchain.com](https://smith.langchain.com) |
| LangGraph Cloud | `LANGGRAPH_API_KEY` | LangGraph Cloud console |

### 3. (Optional) Enable LangSmith tracing

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=risk-manager
```

### 4. Install the pre-push hook

The repo-tracked `pre-commit` pre-push hook runs the shared push gate
before every push. That gate matches the CI `lint-and-test` job by
running `ruff`, `ruff format --check`, `mypy`, `pytest`, and skill
mirror parity as applicable. Locally, it auto-applies Ruff fixes and
formatting; if it rewrites files, stage them and re-push. Activate it
once per clone:

```bash
pre-commit install --hook-type pre-push
```

### Configuration reference

See `agent_runtime/config/README.md` for:

- the full variable reference for all providers and agent runtime backends
- the Python `get_settings()` API for consuming config in code
- testing patterns with `cache_clear()`

---

## Tool-specific setup

### Cursor

Cursor reads `CLAUDE.md` at the repository root, which routes to the correct instruction file for each role. The instruction files contain the full operating rules, reading lists, and stop conditions.

**How to use agents in Cursor:**

1. Open the repository in Cursor
2. Start a new chat or agent session
3. Tell the agent which role to use: "You are the coding agent for this repository"
4. Paste the filled invocation template, or describe the task and let `CLAUDE.md` guide the agent to the right instruction file
5. The agent reads `AGENTS.md`, then the role-specific instruction, then the task-specific context

**Cursor-specific features:**

- `CLAUDE.md` is automatically read by Cursor's agent mode
- Path-scoped instructions in `.github/instructions/` apply to Copilot but not directly to Cursor; use `.cursor/rules/` if you want Cursor-specific path rules
- For long-running sessions, remind the agent of its role boundary if it starts drifting into other roles

**Recommended workflow:**

- Use separate chat sessions for PM, coding, and review work
- Do not ask one session to plan, implement, and review in a single pass
- For coding, start from a fresh branch and keep the scope narrow
- For review, point the agent to the PR diff and linked artifacts

### VS Code with GitHub Copilot

VS Code uses `.github/copilot-instructions.md` for repository-wide Copilot behavior and `.github/instructions/*.instructions.md` for path-scoped rules. The custom agent profiles in `.github/agents/` are available when using GitHub Copilot coding agent.

**How to use agents in VS Code Copilot Chat:**

1. Open the repository in VS Code
2. Copilot automatically reads `.github/copilot-instructions.md` for general behavior
3. When editing files matching a path pattern, Copilot reads the corresponding `.github/instructions/*.instructions.md`
4. For agent-specific work, paste the filled invocation template into Copilot Chat
5. The invocation template tells the agent to read its standing instruction file

**How to use GitHub Copilot coding agent:**

1. Create a GitHub issue with the implementation brief from the PM agent
2. Include the linked work item, PRD, ADRs, target area, and out-of-scope in the issue body
3. Assign the issue to Copilot coding agent, or ask Copilot to create a PR from the issue
4. Copilot reads `.github/agents/coding.agent.md`, which points to `prompts/agents/coding_agent_instruction.md`
5. Wait for the draft PR, then run review with a separate review agent session

**Custom agents in Copilot Chat:**

The `.github/agents/*.agent.md` files define custom agents that can be invoked with `@agent-name` in Copilot Chat. Each one is a thin pointer that tells the agent to read its canonical instruction file.

### Claude Code

Claude Code reads `CLAUDE.md` at the repository root on session start. This file routes to the correct instruction file based on the session role.

**How to use agents in Claude Code:**

1. Open the repository in your terminal
2. Start a Claude Code session
3. Claude reads `CLAUDE.md` automatically, which instructs it to use one bounded role per session
4. Tell Claude which role to use, or paste a filled invocation template
5. Claude reads `AGENTS.md` and the role-specific instruction file before starting work

Recommended workflow for a full delivery cycle:

```text
Session 1 (PM):
  "You are the PM agent. Read prompts/agents/pm_agent_instruction.md.
   Assess whether WI-X.Y.Z is coding-ready."
  → get the implementation brief
  → close the session

Session 2 (Coding):
  "You are the coding agent. Read prompts/agents/coding_agent_instruction.md."
  → paste the implementation brief from session 1
  → agent creates branch, implements, tests, opens draft PR
  → close the session

Session 3 (Review):
  "You are the review agent. Read prompts/agents/review_agent_instruction.md."
  → point to the PR from session 2
  → agent returns pass/fail with findings
  → close the session
```

Do not reuse a PM session for coding, or a coding session for review. The role boundary is the governance boundary.

### OpenAI Codex

Codex supports parallel supervised agent sessions, making it well-suited for the multi-agent relay. Each session can run a different role against the same repository.

**How to use agents in Codex:**

1. Start a Codex session for the PM role
2. The session reads `AGENTS.md` (Codex reads this automatically in many configurations)
3. Paste the filled PM invocation template
4. Get the implementation brief
5. Start a separate Codex session for coding, using the brief from step 4
6. Start a separate Codex session for review after the draft PR exists

**Codex with the agent runtime (semi-autonomous):**

The repository includes an `agent_runtime/` orchestrator that can dispatch work to Codex automatically. When configured with the `codex_exec` backend, the runtime:

1. Scans work-item state and open PR state
2. Decides the next relay action (PM / coding / review)
3. Allocates an isolated git worktree for the run
4. Dispatches the runner prompt to `codex exec`
5. Persists the structured outcome in SQLite
6. Advances to the next step or stops at a human gate

To enable autonomous Codex execution:

```bash
export AGENT_RUNTIME_PM_BACKEND=codex_exec
export AGENT_RUNTIME_CODING_BACKEND=codex_exec
export AGENT_RUNTIME_REVIEW_BACKEND=codex_exec
```

Optional model and binary settings:

```bash
export AGENT_RUNTIME_PM_CODEX_BIN=codex
export AGENT_RUNTIME_PM_CODEX_MODEL=gpt-5
export AGENT_RUNTIME_CODING_CODEX_BIN=codex
export AGENT_RUNTIME_CODING_CODEX_MODEL=gpt-5
export AGENT_RUNTIME_REVIEW_CODEX_BIN=codex
export AGENT_RUNTIME_REVIEW_CODEX_MODEL=gpt-5
```

To enable automatic draft-PR publication after completed coding runs:

```bash
export AGENT_RUNTIME_CODING_PR_BACKEND=gh_draft
```

See `agent_runtime/README.md` for full configuration and `agent_runtime/manual_supervisor_workflow.md` for the operator recipe.

## Autonomous and semi-autonomous operation

### Manual mode (default)

The operator copies invocation templates, fills in placeholders, pastes them into agent sessions, and makes all handoff decisions manually. This is the safest mode and works with any tool.

### Semi-automatic mode (agent runtime, manual agents)

The `agent_runtime` orchestrator decides *what* should happen next, allocates isolated worktrees, and generates the runner prompt. The operator launches the actual agent session manually using the generated prompt, then records the outcome back into the runtime.

```bash
# ask the runtime what to do next
.venv/bin/python -m agent_runtime --dispatch

# → runtime returns: action, work_item_id, runner.name, runner.prompt, worktree.path
# → operator opens the worktree and runs the agent manually
# → operator records the outcome:

.venv/bin/python -m agent_runtime \
  --complete-run <run_id> \
  --outcome-status ready \
  --summary "WI-1.1.9 is coding-ready." \
  --release-after-complete
```

### Supervised autonomous mode (agent runtime + codex backends)

With the `codex_exec` backends enabled, the runtime can execute PM, coding, and review agents automatically:

```bash
# run one supervised cycle
.venv/bin/python -m agent_runtime --run-once

# run the supervised poll loop
.venv/bin/python -m agent_runtime --poll --poll-interval-seconds 300 --max-iterations 12
```

The supervisor loop:

- Acquires a single-repo lock
- Dispatches one eligible runner per iteration
- Continues automatically after completed runs
- Sleeps on `wait_for_reviews` and `noop`
- Stops cleanly on human gates (`human_merge`, `human_update_repo`) and failed runs
- Persists all state in SQLite at `.agent_runtime/state.db`

The human merge gate is always enforced. Even in fully autonomous mode, the runtime stops at merge and waits for a human decision.

### Simulation mode (no real agents)

You can test relay decisions without real agent execution:

```bash
.venv/bin/python -m agent_runtime --list-scenarios
.venv/bin/python -m agent_runtime --simulate ready-no-pr
.venv/bin/python -m agent_runtime --simulate unresolved-review
.venv/bin/python -m agent_runtime --simulate failing-ci-pr
```

## Common workflows

### Nightly delivery loop

1. Fetch latest `main` and fast-forward
2. PM agent chooses one ready slice
3. If not ready, route to issue planner or PRD/spec work
4. Coding agent implements and opens draft PR
5. Wait for Gemini and Copilot bot comments
6. Review agent triages all comments (must fix / optional / not applicable)
7. Coding agent applies accepted fixes
8. PM agent produces a morning summary (mergeable / blocked / needs decision)

### Repo-health audit

Run on a separate cadence from delivery work:

1. Fetch latest `main` and fast-forward
2. Drift monitor agent runs on current `main`
3. PM agent or human triages findings into the correct owner queue
4. Route canon gaps to PRD, ADR, or spec work
5. Route implementation drift to coding or review only when canon is already clear
6. Human decides any policy, architecture, or source-of-truth conflict

### Unblocking a stuck work item

When the PM agent says a work item is `BLOCKED`:

1. Read the blocker description from the PM assessment
2. If the blocker is a missing contract or status semantic: invoke the PRD/spec author to fill the gap
3. If the blocker is a missing prerequisite slice: invoke the issue planner to create it
4. If the blocker is an architecture decision: create or request an ADR (human decision)
5. After the blocker is resolved, rerun the PM agent to reassess readiness

## Stop conditions and escalation

Every agent role has explicit stop conditions documented in its instruction file. When an agent hits a stop condition, it should:

1. Stop the current task
2. Describe the blocker precisely
3. Route it to the correct owner (PM, PRD/spec, ADR, or human)

Common stop conditions across all roles:

- The work item and PRD conflict
- An ADR is missing for a blocking architecture decision
- The agent would need to widen scope beyond its approved boundary
- The agent would need to invent contracts or semantics not defined in existing canon

The relay is designed to stop and escalate rather than guess. A stopped agent with a clear blocker is more valuable than a running agent that silently invents the wrong thing.

## File reference

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Master role definitions, handoff model, repo rules |
| `CLAUDE.md` | Claude Code / Cursor role routing |
| `GEMINI.md` | Gemini role routing |
| `.github/agents/*.agent.md` | Copilot custom agent profiles |
| `.github/copilot-instructions.md` | Copilot repository-wide instructions |
| `.github/instructions/*.instructions.md` | Copilot path-scoped instructions |
| `prompts/agents/*_instruction.md` | Standing instructions (canonical source of truth) |
| `prompts/agents/invocation_templates/*.md` | Per-task prompt templates with placeholders |
| `docs/guides/overnight_agent_runbook.md` | Operational runbook for the delivery relay |
| `docs/guides/agent_workflow_guide.md` | Tool-specific usage patterns |
| `docs/guides/agent_framework.md` | This document |
| `agent_runtime/README.md` | Automated delivery orchestration |
| `agent_runtime/manual_supervisor_workflow.md` | Semi-automatic operator recipe |

# Agent Workflow Guide

## Purpose

This guide explains how to use the project agents with external coding tools such as Claude Code, Codex, Cursor, and GitHub Copilot.

It is intentionally tool-agnostic at the workflow level. The same operating model should apply regardless of which coding surface you use.

## The core agent roles

### PM Agent

The PM agent is responsible for:

- sequencing work
- keeping PRs narrow
- identifying dependencies and blockers
- making sure the implementation still follows the target operating model

Use the PM agent when you need to answer:

- what should we build next?
- how do we split this PRD into implementation slices?
- which work item blocks which other work item?
- is this PR too broad?

### Coding Agent

The coding agent is responsible for:

- implementing one scoped slice faithfully
- preserving contract fidelity
- writing tests
- avoiding architecture drift

Use the coding agent when you already know the slice and want code, tests, and a PR.

### Review Agent

The review agent is responsible for:

- checking scope fidelity
- checking contract fidelity
- checking degraded-state handling
- checking replay safety
- spotting architecture drift

Use the review agent before merging and whenever an implementation feels slightly suspicious.

### Drift Monitor Agent

The drift monitor agent is responsible for:

- auditing repo-wide coherence
- detecting contradiction, duplication, stale guidance, and boundary erosion
- surfacing document sprawl or weak source-of-truth signaling
- routing findings to the correct owner

Use the drift monitor when you need to answer:

- is the repository still internally coherent?
- have docs, prompts, work items, and implementation drifted apart?
- are there duplicate or conflicting sources of truth?
- is the repo becoming sprawling or directionless?

### Issue Planner Agent

The issue planner agent is responsible for:

- decomposing PRDs into small work items
- making dependencies explicit
- ensuring acceptance criteria are concrete

Use it when a PRD is still too large for a coding agent to execute cleanly.

## Recommended operating loop

1. PM agent chooses the next slice
2. Issue planner agent refines the slice into a work item if needed
3. Coding agent implements the slice
4. Review agent checks the result
5. Human decides whether to merge or send back

This loop keeps the work disciplined and prevents a coding agent from becoming a wandering architect.

## Separate repo-health loop

Use the drift monitor on a separate cadence:

1. run a repo-health audit on current `main`
2. triage findings through PM or a human
3. route approved follow-up into PRD, spec, coding, or review work

Do not let the repo-health audit replace PR review or implementation review on a live slice.

## Tool-specific usage patterns

## Claude Code

Best use:

- one issue or work item at a time
- explicit implementation briefs
- local repo work with strong file context

Recommended pattern:

1. open the repo
2. paste the linked work item and PRD summary
3. instruct Claude Code to stay inside scope
4. ask it to produce code plus tests plus a short assumptions note
5. run review with either a review agent prompt or another model

Good prompt shape:

- here is the work item
- here is the PRD context
- here are the files you may change
- do not widen scope
- add tests
- summarize assumptions and edge cases

## Codex

OpenAI Codex can be useful for parallel work, longer-running coding tasks, and supervised multi-agent workflows. Refer to the official product page for current capabilities and supported surfaces: [OpenAI Codex](https://openai.com/codex/).

Best use:

- parallel implementation slices
- longer-running coding tasks
- supervised multi-agent work

Recommended pattern:

- use one Codex session for PM sequencing
- use one session for the coding slice
- use a separate session for review
- use a separate session for drift monitoring when doing repo-health audits
- keep each session attached to a narrow artifact set

For this repo, do not ask one Codex session to redesign architecture and implement a slice at the same time.

## Cursor

Cursor supports reusable rules, including project rules stored in `.cursor/rules`, user rules, and legacy `.cursorrules`. Refer to the official documentation for current rule behavior and project configuration.

Best use:

- repository-scoped coding instructions
- path-specific implementation behavior
- repeated local workflows

Recommended setup for this repo:

- create project rules for coding discipline
- create separate rules for deterministic services versus walker logic
- keep the rules short and operational
- point Cursor to the canon docs for mission and PRD behavior

Good Cursor rule themes:

- preserve deterministic core behavior
- do not invent status semantics
- keep PRs small
- always add tests
- respect scope-aware hierarchy semantics

## GitHub Copilot coding agent

GitHub Copilot coding agent can work on issues or open pull requests, works in the background, and can be customized through repository custom instructions, MCP servers, custom agents, and hooks. GitHub also documents custom agent profiles and repository custom instructions files such as `copilot-instructions.md` and path-specific `.instructions.md` files. See [About GitHub Copilot coding agent](https://docs.github.com/en/copilot/using-github-copilot/coding-agent/about-github-copilot-coding-agent), [Adding repository custom instructions for GitHub Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions), [Creating custom agents for GitHub Copilot](https://docs.github.com/en/copilot/how-tos/provide-context/use-custom-agents), and [Adding personal custom instructions for GitHub Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-personal-instructions).

Best use:

- issue-driven implementation on GitHub
- repository custom instructions
- specialized custom agents per task type

Recommended setup for this repo:

- repository-wide instructions for coding discipline
- one custom agent for coding
- one custom agent for review
- one custom agent for PM or issue planning
- one optional custom agent for drift monitoring
- optional hooks for build, test, lint, and validation

Good pattern:

- assign a narrow issue to Copilot coding agent
- include linked PRD and work item in the issue body
- require tests and a concise assumptions note
- review the PR with your review agent prompt before merge

## How to choose which tool to use

### Use Claude Code when

- you want tight interactive control
- the slice is local and code-heavy
- you want to iterate rapidly on a small implementation

### Use Codex when

- you want multiple supervised agent threads
- you want to separate PM, coding, and review flows
- the work may run longer and benefit from parallelism

### Use Cursor when

- you want persistent repo rules close to your editor
- you want local implementation support with file-aware context
- you want path-scoped instructions

### Use Copilot coding agent when

- the work is already framed as GitHub issues and PRs
- you want repo-integrated background implementation
- you want custom agents and repo instructions living close to GitHub workflow

## Recommended repo-visible agent setup

For this project, keep the canonical repo-visible instructions aligned to the sources that already exist:

- `AGENTS.md` for coding-agent and repository operating instructions
- `prompts/README.md` as the index for the prompt set
- prompt files in `prompts/` for PM, review, issue planning, drift monitoring, PRD generation, and related workflow templates

If you later add a dedicated coding-agent prompt file, make sure this guide and `prompts/README.md` are updated together.

Then map those sources into whichever tool you use:

- Cursor rules
- Copilot custom instructions or custom agents
- Claude Code prompt templates
- Codex session briefs

## Human role in the loop

The human should still decide:

- whether the slice is correctly scoped
- whether the technology decision is right
- whether the agent widened scope
- whether a PR is ready to merge
- whether a contract change should be accepted

The agents help you move faster. They do not get to become the bank.

# Overnight Agent Runbook

## Purpose

This runbook explains how to operate the repository's agent governance model in practice.

It is designed to stop one coding surface from doing all jobs at once. The goal is a gated relay:

1. PM agent decides the next bounded slice
2. issue planner agent splits work only if needed
3. coding agent implements one slice
4. review agent reviews the PR and any bot feedback
5. human decides whether to merge

## Core rule

Do not ask one agent session to:

- redesign architecture
- rewrite PRDs
- implement code
- review its own implementation
- decide merge readiness

in one pass.

That collapses the governance model.

## Freshness rule

Before any PM, coding, or review cycle:

1. git fetch origin
2. git switch main
3. git pull --ff-only origin main

For reviews, then checkout the latest PR head. For coding, create a fresh branch from main.

New work must begin from up-to-date `main`.

Each bounded slice should use its own fresh branch created from current `main`.

Agents must not rely on stale local state when the repository, PRs, or canon documents may have changed.

## Canonical handoff chain

### Step 1: PM agent

Inputs:

- `docs/delivery/01_pm_operating_model.md`
- `docs/delivery/02_readiness_and_dependency_framework.md`
- `docs/delivery/03_slice_sizing_and_pr_strategy.md`
- `docs/delivery/04_review_triage_and_escalation.md`
- `docs/guides/pm_quality_checklist.md`
- `work_items/READY_CRITERIA.md`
- target work item
- linked PRD
- linked ADRs
- current open PR state

Outputs:

- ready or blocked decision
- exact implementation slice
- explicit dependencies
- target area
- stop conditions for the coding agent

### Step 2: Issue planner agent

Run only when the PM agent says the work item is too broad or ambiguous.

Inputs:

- linked PRD
- linked ADRs
- current work item

Outputs:

- revised work item
- narrower work-item split
- dependencies and target areas

### Step 3: Coding agent

Inputs:

- assigned work item
- linked PRD
- linked ADRs
- local target files

Outputs:

- code and tests
- assumptions note
- draft PR

### Step 4: Review agent

Inputs:

- assigned work item
- linked PRD
- linked ADRs
- changed files
- tests
- Gemini and Copilot review comments if present

Outputs:

- pass or fail
- material findings
- missing tests
- required changes before merge

### Step 5: Human decision

Human remains responsible for:

- merge approval
- architecture changes
- ADR acceptance
- scope correction

## Recommended nightly loop

1. Fetch latest `main` and fast-forward local `main`
2. PM agent chooses one ready slice
3. If not ready, route to issue planner or spec work
4. Coding agent implements and opens draft PR
5. Wait for Gemini and Copilot comments
6. Review agent triages all comments:
   - must fix
   - optional
   - not applicable
7. Coding agent applies accepted fixes
8. PM agent produces a morning summary:
   - mergeable
   - blocked
   - needs decision
   - superseded

## Stop conditions

The loop should stop and escalate to a human if:

- the work item and PRD conflict
- an ADR is missing for a blocking decision
- the coding agent would need to widen scope
- the review agent finds contract drift
- Gemini or Copilot identifies a real blocking defect
- the branch diverges materially from the intended slice

## Practical prompts

### PM agent prompt

Use a prompt of this shape:

```text
You are the PM agent for this repository.

Read:
- work_items/READY_CRITERIA.md
- <WORK_ITEM>
- <LINKED_PRD>
- <LINKED_ADRS>

Decide:
1. Is this item actually ready?
2. What exact files or areas should the coding agent touch?
3. What must the coding agent not do?
4. What would block implementation?

Return:
- ready or blocked
- dependencies
- target area
- a one-paragraph implementation brief
```

### Coding agent prompt

```text
Implement exactly one bounded slice.

Read:
- <WORK_ITEM>
- <LINKED_PRD>
- <LINKED_ADRS>
- local target files only

Rules:
- do not widen scope
- preserve contract fidelity
- add tests
- stop if a blocking ambiguity requires an ADR or PRD change

Return:
- code changes
- tests
- short assumptions note
```

### Review agent prompt

```text
Review this PR against:
- <WORK_ITEM>
- <LINKED_PRD>
- <LINKED_ADRS>
- changed files
- tests
- Gemini and Copilot review comments

Return:
1. pass or fail
2. material findings
3. missing tests
4. which external review comments are valid
5. required changes before merge
```

## Tool-specific operation

### Codex CLI or Codex app

Use separate sessions or threads:

1. PM session
2. coding session
3. review session

Do not reuse the same session for all three roles if you want the governance boundaries to hold.

Recommended cadence:

1. fetch and fast-forward local `main`
2. start PM session and get the implementation brief
3. create a fresh branch from current `main`
4. start coding session using only that brief plus linked artifacts
5. push draft PR
6. wait for GitHub comments
7. start review session to triage the PR and bot comments
8. if fixes are required, return to the coding session with only the accepted findings

### Claude Code

Use separate terminal sessions or separate invocations.

Recommended cadence:

1. fetch and fast-forward local `main`
2. open Claude Code for PM work
3. ask it for a readiness and implementation brief only
4. close or stop that PM session
5. create a fresh branch from current `main`
6. open a fresh Claude Code session for coding
7. open a fresh Claude Code session for review after the PR exists

### GitHub Copilot coding agent

Use Copilot for the coding step, not the full governance chain.

Recommended cadence:

1. fetch and fast-forward local `main`
2. use your PM agent locally to produce the final bounded implementation brief
3. open or update a GitHub issue with:
   - linked work item
   - linked PRD
   - linked ADRs
   - exact target area
   - explicit out-of-scope reminder
4. create the implementation branch from current `main`
5. assign the issue to Copilot coding agent or ask Copilot to create a PR
6. wait for the Copilot PR
7. run your review agent locally against the PR plus bot comments

## Morning checklist

Every morning, review:

- open draft PRs
- unresolved Gemini comments
- unresolved Copilot comments
- PM morning summary
- any slice that should be split instead of merged

## Rule for this repository

Until deterministic foundations are implemented and stable:

- PM agent may sequence work
- coding agent may implement only ready slices
- review agent may block freely
- human remains the merge authority

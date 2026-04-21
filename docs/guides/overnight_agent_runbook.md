# Overnight Agent Runbook

## Purpose

This runbook explains how to operate the repository's agent governance model in practice. For a comprehensive overview of the agent framework — what the agents are, how they work, and how to set them up across different tools — see `docs/guides/agent_framework.md`.

It is designed to stop one coding surface from doing all jobs at once. The goal is a gated relay:

1. PM agent decides the next bounded slice
2. PRD / spec author or issue planner refines scope when needed
3. coding agent implements one slice
4. review agent reviews the PR and any bot feedback
5. human decides whether to merge

The repository also uses a separate drift-monitoring control for repo-wide health checks. That control sits outside the delivery relay and feeds findings back into PM or human triage.

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

Before any manual direct-mode PM, coding, review, or drift-monitor cycle:

1. git fetch origin
2. git switch main
3. git pull --ff-only origin main

For manual review work, then checkout the latest PR head. For manual coding, create a fresh branch from main.

New work must begin from up-to-date `main`.

Each bounded slice should use its own fresh branch created from current `main`.

Agents must not rely on stale local state when the repository, PRs, or canon documents may have changed.

Repo-health audits should also run from current `main` so they do not report drift against stale local guidance.

In runtime-managed mode, refresh the control checkout before dispatch and then
do the real PM/spec/issue-planner/coding/review/drift-monitor work only inside
the runtime-allocated worktree. Do not switch a runtime-managed session back to
`main`, do not allocate another worktree, and do not create another branch.

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
- `docs/engineering/`
- `docs/guides/coding_quality_checklist.md`
- `docs/guides/performance_review_checklist.md`
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

## Separate repo-health control

### Drift monitor agent

This role is not part of the per-slice implementation handoff.

Inputs:

- `AGENTS.md`
- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/repo_health_audit_checklist.md`
- `prompts/drift_monitor/repo_health_audit_prompt.md`
- `docs/registry/current_state_registry.yaml`
- relevant canon, prompt, work-item, source, and test artifacts

Outputs:

- overall repo health status
- critical, major, and minor drift findings
- sanctioned duplication called out as acceptable
- owner and routing recommendation for each material finding

Use this role to detect:

- contradictory canon
- duplicated or diverging source-of-truth content
- stale guidance
- boundary erosion
- documentation sprawl that weakens governance

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

## Recommended repo-health loop

Run this on a separate cadence from ordinary PR delivery:

1. Fetch latest `main` and fast-forward local `main`
2. Run the drift monitor on current `main`
3. PM agent triages accepted findings into the correct owner queue
4. Route canon gaps to PRD, ADR, or methodology/spec work
5. Route implementation drift to coding or review only when canon is already clear
6. Human decides any policy, architecture, or source-of-truth conflict

## Stop conditions

The loop should stop and escalate to a human if:

- the work item and PRD conflict
- an ADR is missing for a blocking decision
- the coding agent would need to widen scope
- the review agent finds contract drift
- Gemini or Copilot identifies a real blocking defect
- the branch diverges materially from the intended slice

## Invocation templates

Use the invocation templates in `prompts/agents/invocation_templates/` for the expected prompt shape for each role:

- `prompts/agents/invocation_templates/pm_invocation.md`
- `prompts/agents/invocation_templates/prd_spec_invocation.md`
- `prompts/agents/invocation_templates/issue_planner_invocation.md`
- `prompts/agents/invocation_templates/coding_invocation.md`
- `prompts/agents/invocation_templates/review_invocation.md`
- `prompts/agents/invocation_templates/drift_monitor_invocation.md`

Copy the relevant template, fill in the placeholders, and paste as the prompt to your agent.

## Tool-specific operation

### Codex CLI or Codex app

Use separate sessions or threads:

1. PM session
2. coding session
3. review session
4. optional drift-monitor session for repo-health audits

Do not reuse the same session for all delivery roles if you want the governance boundaries to hold.

Recommended cadence:

1. fetch and fast-forward local `main`
2. start PM session and get the implementation brief
3. create a fresh branch from current `main`
4. start coding session using only that brief plus linked artifacts
5. push draft PR
6. wait for GitHub comments
7. start review session to triage the PR and bot comments
8. if fixes are required, return to the coding session with only the accepted findings

For repo-health work, run a separate drift-monitor session against current `main` and route the resulting findings through PM or a human rather than converting them directly into ad hoc coding.

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
- drift monitor may audit repo health and route findings
- human remains the merge authority

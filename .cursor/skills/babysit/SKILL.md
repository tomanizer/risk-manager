---
name: babysit
description: >-
  Keep a GitHub PR merge-ready: triage review comments, resolve inline threads,
  fix merge conflicts when intent is clear, and repair merge-blocking CI with
  small scoped commits until checks are green. Tool-agnostic — use in Cursor,
  Claude Code, Codex, Copilot, or any agent that can run git and gh.
---
<!-- GENERATED SKILL MIRROR: do not edit directly -->


# babysit

## Mandatory first output

Before doing anything else, print:

```text
[babysit] Skill active. Working PR merge-readiness...
```

## When to use

- User says **babysit**, **babysit PR**, **`/babysit`**, or **`/babysit 154`** (PR number).
- Review agent or operator wants the branch **green**, **threads resolved**, and **no trivial blockers** before merge.

> **HARD CONSTRAINT — small, scoped fixes only:** Only small, scoped fixes for CI, merge hygiene, or obvious comment-driven nits. No feature work or contract changes unless the user explicitly widens scope.
>
> **HARD CONSTRAINT — do not merge:** Do not merge the PR unless the user explicitly asks you to merge; babysit stops at merge-ready.
>
> **HARD CONSTRAINT — stop on judgment calls:** If a conflict or comment requires product or architecture judgment, stop and ask instead of guessing.

## Inputs

1. **PR number** — from the user message (e.g. `154`). If missing, ask: `Which PR number should I babysit?`
2. **Repo** — current working tree should be this repository (`risk-manager`), with `origin` pointing at GitHub.

## Prerequisites

- **`gh` CLI** authenticated (`gh auth status`).
- **git** with fetch access to `origin`.

## Procedure (loop until stable or blocked)

### 1. Snapshot PR state

```bash
gh pr view <PR#> --json title,state,url,mergeable,mergeStateStatus,baseRefName,headRefName,reviewDecision
gh pr checks <PR#>
```

Report: mergeable, merge-state (e.g. blocked by rules), and which checks passed / failed / pending.

If checks are **still running**, wait and re-run `gh pr checks` before declaring done.

### 2. Checkout PR head (before any local commits)

```bash
gh pr checkout <PR#>
```

Confirm your branch matches the PR head (`headRefName` from step 1). If you only read state and make **no commits**, checkout is optional; once you edit or commit, you must be on the PR head branch.

### 3. Branch freshness and conflicts

```bash
git fetch origin
```

Use **`baseRefName`** from step 1 (often `main`, not always). Compare the PR head to **`origin/<baseRefName>`**.

- If the PR branch is **behind** `origin/<baseRefName>` and CI or review expect an updated base, merge or rebase per repo convention (prefer **merge** from base into PR branch if unsure, to avoid force-push surprises).
- If **merge conflicts** exist, open conflicted files. Resolve only when the correct resolution is obvious from both sides; otherwise stop with a short conflict summary for the human.

### 4. CI failures attributable to this PR

For each **failing** required check:

- **Lint / type / tests** tied to files touched on the PR: fix minimally, run the same commands locally if possible (`ruff`, `mypy`, `pytest` as in `.github/workflows/ci.yml`), **commit**, **push** the PR head branch, then re-check `gh pr checks`.
- **Unrelated** (flaky, infra, main broken): note on the PR or in your summary; do not spend unbounded time unless the user asks.

Repeat until required checks are green or you hit a hard blocker.

### 5. Comments and review threads

**Inline review threads** (Copilot, Gemini, humans on files):

1. List threads and resolution state. Runnable example (set `OWNER`, `REPO`, `PR_NUMBER`):

```bash
gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") { pullRequest(number: PR_NUMBER) { reviewThreads(first: 50) { nodes { id isResolved comments(first: 20) { nodes { author { login } body } } } } } } }'
```

Same query inline for reference:

```graphql
query {
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 50) {
        nodes {
          id
          isResolved
          comments(first: 20) {
            nodes { author { login } body }
          }
        }
      }
    }
  }
}
```

1. For each **unresolved** thread: **valid** → fix or track in required work; **not applicable / already fixed** → reply briefly, then **resolve**:

```graphql
mutation {
  resolveReviewThread(input: { threadId: "PRRT_..." }) {
    thread { id isResolved }
  }
}
```

Batch several `resolveReviewThread` fields in one `mutation { a: ... b: ... }` when GitHub allows.

1. **Re-query** threads after each push that might address feedback.

**Timeline / issue comments** (not file-attached): reply when triage needs a public answer; there is no `resolveReviewThread` for those.

### 6. Closing summary

Return a short report:

- PR URL, mergeable / merge-state, **CI** outcome
- **Threads**: how many resolved this session, any left open and why
- **Commits pushed** (if any) and **remaining blockers** (reviews, branch protection, unclear conflicts)

## Cross-references

- Review agent thread hygiene: `prompts/agents/review_agent_instruction.md` (GitHub actions during review).
- Freshness before heavy git moves: `AGENTS.md` (fetch main, pull, then PR head when reviewing).

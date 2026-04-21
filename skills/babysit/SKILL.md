---
name: babysit
description: >-
  Keep a GitHub PR merge-ready: triage review comments, resolve inline threads,
  wait for draft-stage Gemini feedback, promote the PR when ready, verify the
  Copilot review pass, fix merge conflicts when intent is clear, and repair
  merge-blocking CI with small scoped commits until checks are green.
  Tool-agnostic — use in Cursor, Claude Code, Codex, Copilot, or any agent
  that can run git and gh.
---

# babysit

## Mandatory first output

Before doing anything else, print:

```text
[babysit] Skill active. Working PR merge-readiness...
```

## When to use

- User says **babysit**, **babysit PR**, **`/babysit`**, or **`/babysit 154`** (PR number).
- Review agent or operator wants the branch **green**, **threads resolved**, and **no trivial blockers** before merge.
- Team workflow uses a **draft PR -> Gemini review -> ready for review -> Copilot review** relay and wants that sequence handled with minimal manual prompting.

> **HARD CONSTRAINT — small, scoped fixes only:** Only small, scoped fixes for CI, merge hygiene, or obvious comment-driven nits. No feature work or contract changes unless the user explicitly widens scope.
>
> **HARD CONSTRAINT — do not merge:** Do not merge the PR unless the user explicitly asks you to merge; babysit stops at merge-ready.
>
> **HARD CONSTRAINT — stop on judgment calls:** If a conflict or comment requires product or architecture judgment, stop and ask instead of guessing.
>
> **HARD CONSTRAINT — bounded waiting only:** Poll for bot activity on a bounded loop (for example, every 30 seconds for up to 15 minutes) and then report what is still missing. Do not wait forever.

## Inputs

1. **PR number** — from the user message (e.g. `154`). If missing, ask: `Which PR number should I babysit?`
2. **Repo** — current working tree should be this repository (`risk-manager`), with `origin` pointing at GitHub.

## Prerequisites

- **`gh` CLI** authenticated (`gh auth status`).
- **git** with fetch access to `origin`.
- GitHub API access via `gh api` for reviews, comments, requested reviewers, and GraphQL thread resolution.

## Procedure (loop until stable or blocked)

### 1. Snapshot PR state

```bash
gh pr view {pr_number} --json title,state,isDraft,url,mergeable,mergeStateStatus,baseRefName,headRefName,reviewDecision
gh pr checks {pr_number}
```

Report: mergeable, merge-state (e.g. blocked by rules), and which checks passed / failed / pending.

If checks are **still running**, wait and re-run `gh pr checks` before declaring done.

Capture `{owner}` and `{repo}` once from `origin` or `gh repo view --json name,owner`.

### 2. Checkout PR head (before any local commits)

```bash
gh pr checkout {pr_number}
```

Confirm your branch matches the PR head (`headRefName` from step 1). If you only read state and make **no commits**, checkout is optional; once you edit or commit, you must be on the PR head branch.

### 3. Branch freshness and conflicts

```bash
git fetch origin
```

Use **`baseRefName`** from step 1 (often `main`, not always). Compare the PR head to **`origin/<baseRefName>`**.

- If the PR branch is **behind** `origin/<baseRefName>` and CI or review expect an updated base, merge or rebase per repo convention (prefer **merge** from base into PR branch if unsure, to avoid force-push surprises).
- If **merge conflicts** exist, open conflicted files. Resolve only when the correct resolution is obvious from both sides; otherwise stop with a short conflict summary for the human.

### 4. Bot review inventory helpers

Use these endpoints repeatedly during the babysit loop:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews
gh api repos/{owner}/{repo}/issues/{pr_number}/comments
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments
gh api repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers
```

Use a GraphQL thread query when you need thread ids and resolution state:

```bash
gh api graphql -f query='query($owner:String!, $repo:String!, $pr:Int!) { repository(owner: $owner, name: $repo) { pullRequest(number: $pr) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 20) { nodes { author { login } body url createdAt } } } } } } }' -F owner={owner} -F repo={repo} -F pr={pr_number}
```

Use the exact bot identities and structures already observed in this repository:

- **Gemini review login via REST:** `reviews[].user.login == "gemini-code-assist[bot]"` with a body starting `## Code Review`
- **Gemini inline thread login via GraphQL:** `reviewThreads.nodes[].comments.nodes[].author.login == "gemini-code-assist"` with severity badges and often a ```suggestion``` block
- **Gemini fallback issue-comment shape:** `issues/{pr_number}/comments[].user.login == "gemini-code-assist[bot]"` with a note that Gemini could not generate a review for the file types involved
- **Copilot review login via REST:** `reviews[].user.login == "copilot-pull-request-reviewer[bot]"` with a body starting `## Pull request overview`
- **Copilot inline thread login via GraphQL:** `reviewThreads.nodes[].comments.nodes[].author.login == "copilot-pull-request-reviewer"` with focused file-level comments and occasional ```suggestion``` blocks
- **Copilot requested-reviewer shape via REST:** `requested_reviewers.users[].login` commonly includes `Copilot`

Treat these observed shapes as the default arrival signals:

- **Gemini arrived** when reviews or issue comments use `user.login == "gemini-code-assist[bot]"`, or review threads use `author.login == "gemini-code-assist"`.
- **Copilot arrived** when reviews use `user.login == "copilot-pull-request-reviewer[bot]"`, review threads use `author.login == "copilot-pull-request-reviewer"`, or `requested_reviewers.users[].login` includes `Copilot`.

If the PR already has Gemini or Copilot activity when babysit starts, treat that as the relevant review having already arrived; do not wait for a second copy before triaging.

### 5. Draft-stage Gemini gate

If `isDraft` is `true`, babysit should **not** move the PR to ready-for-review immediately.

1. Poll the review inventory helpers on a bounded loop until Gemini review activity appears, or the wait deadline expires.
2. Once Gemini has arrived, triage it before changing PR state:
   - **valid** -> apply the minimal sensible fix, run targeted verification (see step 8), commit, push
   - **partial** -> fix the valid subset, reply with what remains or why scope stops here
   - **not applicable / already fixed** -> reply briefly, then resolve the thread if it is inline
3. Re-query threads after each push. Keep going until there are no actionable Gemini threads left or you hit a human-judgment blocker.
4. If Gemini never arrives before the deadline, stop and report that the draft PR is still waiting on Gemini review. Do **not** automatically move it to ready in that case.

### 6. Promote to ready and verify Copilot trigger

After Gemini has been triaged on a draft PR:

```bash
gh pr ready {pr_number}
```

If `isDraft` is already `false`, skip the `gh pr ready` command and go straight to Copilot-trigger verification.

Then verify that Copilot review has actually been triggered.

1. Poll `requested_reviewers`, reviews, issue comments, and review comments on a bounded loop.
2. A pending requested reviewer where `requested_reviewers.users[].login` includes `Copilot` counts as **triggered but not yet completed**.
3. A Copilot-authored review/comment from the observed Copilot identities above counts as **arrived**.
4. If no Copilot signal appears before the deadline, report that automatic Copilot review was **not observed** after the PR became ready. Treat that as a workflow blocker or manual follow-up item rather than guessing.

Important nuance: GitHub documents that Copilot automatic review normally fires when a PR is created open or the **first** time a draft PR is switched to open. GitHub also documents that Copilot does **not** automatically re-review later pushes unless the repo has the relevant setting enabled. If Copilot already reviewed the draft PR earlier, triage that existing Copilot feedback and do not assume a second automatic review will appear after `gh pr ready`.

### 7. Comments and review threads

Run this step after Gemini arrives, again after making the PR ready, again after Copilot arrives, and again after each push that may satisfy feedback.

**Inline review threads** (Copilot, Gemini, humans on files):

1. List threads and resolution state with the GraphQL query from step 4.
2. For each **unresolved** thread: **valid** -> fix or track in required work; **not applicable / already fixed** -> reply briefly, then **resolve**:

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

### 8. CI failures attributable to this PR

For each **failing** required check:

- **Lint / type / tests** tied to files touched on the PR: fix minimally, run the same commands locally if possible (`ruff`, `mypy`, `pytest` as in `.github/workflows/ci.yml`), **commit**, **push** the PR head branch, then re-check `gh pr checks`.
- **Unrelated** (flaky, infra, main broken): note on the PR or in your summary; do not spend unbounded time unless the user asks.

Repeat until required checks are green, the bot-review loop is stable, or you hit a hard blocker.

### 9. Closing summary

Return a short report:

- PR URL, mergeable / merge-state, **CI** outcome
- **Gemini**: whether draft review arrived, what was accepted / declined, and whether the PR was promoted to ready
- **Copilot**: whether trigger was observed, whether review arrived, and any comments still awaiting human judgment
- **Threads**: how many resolved this session, any left open and why
- **Commits pushed** (if any) and **remaining blockers** (reviews, branch protection, unclear conflicts)

## Cross-references

- Review agent thread hygiene: `prompts/agents/review_agent_instruction.md` (GitHub actions during review).
- Freshness before heavy git moves: `AGENTS.md` (fetch main, pull, then PR head when reviewing).

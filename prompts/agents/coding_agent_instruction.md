# Coding Agent Instruction

## Mission

Implement one bounded work item faithfully, deterministically, and with tests.

The coding agent is an implementation worker, not a product strategist and not an architecture owner.

## Required reading order

Before writing code, read in this order:

1. `AGENTS.md`
2. `docs/engineering/01_python_engineering_principles.md`
3. `docs/engineering/02_performance_and_vectorization.md`
4. `docs/engineering/03_data_and_database_performance.md`
5. `docs/engineering/04_library_selection_and_dependency_policy.md`
6. `docs/engineering/05_code_readability_and_documentation.md`
7. `docs/engineering/06_test_strategy_for_deterministic_services.md`
8. `docs/guides/coding_quality_checklist.md`
9. `docs/guides/performance_review_checklist.md`
10. assigned work item
11. linked PRD
12. linked ADRs
13. relevant module, workflow, or prompt documentation
14. local package README files where relevant

## Primary responsibilities

- implement only the assigned slice
- preserve contract fidelity
- keep degraded states explicit
- apply the engineering canon in `docs/engineering/`
- prefer established libraries over custom reinvention
- choose a computation shape that respects performance
- add or update tests with the change
- preserve replayability and evidence behavior where applicable
- leave clear notes when ambiguity remains

## Operating rules

### Stay inside scope

Do not widen scope because adjacent work looks convenient.

### Prefer deterministic implementations

If the work belongs in a deterministic service, do not introduce AI behavior or fuzzy logic.

### Prefer established libraries

Use established libraries such as `numpy`, `scipy`, `pyarrow`, `duckdb`, and `statsmodels` where they fit the workload and are already available in the repository environment rather than inventing custom numerical or data-processing infrastructure.

If introducing one of these dependencies is necessary, make that an explicit dependency change by updating the relevant dependency section in `pyproject.toml` (for example, `[project.dependencies]` or `[project.optional-dependencies]`), include a brief justification, and verify the change in CI.

Treat the approved `[compute]` extra as optional repository capacity, not as guaranteed default CI presence, until a governed slice explicitly depends on it.

### Prefer the right execution shape

For analytical workloads, prefer, when those libraries are already available:

- vectorized `numpy`
- `duckdb` SQL
- `pyarrow` columnar paths

over row-wise Python work when that is the natural shape of the problem.

### Avoid unnecessary abstraction

Do not add extra indirection layers unless they provide clear replay, validation, or boundary value.

### Keep performance visible

If a path is performance-sensitive, make the chosen computation shape and any important tradeoffs obvious in the code and PR summary.

### Keep code readable

Fast code still needs to be easy to read, easy to review, and easy to test.

### Respect typed contracts

Do not rename fields, relax status semantics, or collapse explicit states for convenience.

### Preserve boundaries

- modules own deterministic truth
- walkers own typed interpretation
- orchestrators own workflow state, routing, and gates
- UI owns presentation only

### Make degraded behavior explicit

Missing, partial, blocked, or degraded states must surface clearly in code and tests.

### Add tests with the change

Every meaningful implementation change should include the relevant unit, integration, replay, or fixture coverage expected by the work item and PRD.

Tests should be high-signal and behavior-focused rather than broad but shallow.

## Stop conditions

Stop and report a blocker rather than guessing when:

- the work item and PRD conflict on a contract, status semantic, or error model
- an ADR is missing for a blocking architecture decision
- implementing the slice would require changing contracts or schemas outside the target area
- the slice requires inventing status semantics, error envelopes, or typed contracts not defined in the PRD
- the implementation would need to widen scope beyond the assigned work item
- a dependency that should exist does not yet exist in the codebase

In these cases, stop the implementation, describe the blocker precisely, and route it back to PM or PRD/spec.

## Forbidden behavior

- architecture redesign without an ADR
- hidden fallback behavior
- silent contract drift
- speculative abstractions unrelated to the assigned slice
- custom statistical or numerical code where a standard library would do
- row-wise analytical processing without a clear reason
- unrelated refactors
- mixing multiple work items into one change without explicit PM approval

## Handoff output

After completing the implementation and opening a draft PR, produce a handoff prompt for the next agent. Print it as a copy-paste-ready block so the operator can open a fresh session for the next role without manual template filling.

### If the PR is open and CI is passing

Fill `prompts/agents/invocation_templates/review_invocation.md` with actual values and print:

```text
Paste this into a FRESH Review Agent session (new chat / new Codex session):
```

Followed by the filled prompt. Use these values:

- `<ASSIGNED_WORK_ITEM>` → path to the work item file
- `<LINKED_PRD>` → path to the linked PRD
- `<LINKED_ADRS>` → ADR paths used in this slice
- `<PR_NUMBER>` → the PR number opened
- `<BRANCH_NAME>` → the branch name
- `<CONTEXT — what the PR implements, any known concerns>` → one sentence: what the PR implements and any concerns the review agent should know

### If CI is failing

Do not hand off to review. Fix CI failures before producing the review handoff. If the failure is outside the work item scope or requires a contract decision, stop and print:

```text
BLOCKED — route to PM:
```

Followed by the precise failure and the recommended routing (PM / PRD / ADR / human).

### If you hit a stop condition before opening a PR

Do not produce a review handoff. Print:

```text
BLOCKED — route to PM:
```

Followed by the precise blocker and the recommended routing.

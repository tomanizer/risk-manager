# WI-MAINT-2A

## Status

**READY** - GitHub issue `#196` is open, the contract-first slice is bounded, and no upstream code dependency must land before this foundation work can start.

## Blocker

- None. PM can assign this slice to Coding Agent.

## Linked PRD

None - runtime delivery infrastructure maintenance.

Policy basis: [agent_runtime_modernization_plan.md](../../docs/delivery/plans/agent_runtime_modernization_plan.md), [GitHub issue #196](https://github.com/tomanizer/risk-manager/issues/196), [umbrella issue #195](https://github.com/tomanizer/risk-manager/issues/195), and [agent_runtime_audit_2026-04-21.md](../../docs/guides/agent_runtime_audit_2026-04-21.md).

## Linked ADRs

None required.

## Linked shared infra

None.

## Purpose

Introduce one typed, serializable shared handoff-bundle contract that can become the common context surface for runtime-managed and manual agent invocation flows.

## Scope

- Add a shared handoff bundle module under `agent_runtime/` for governed agent context.
- Define the governed field set for at least:
  - role
  - work item identity and path
  - checkout context
  - linked PRD
  - linked ADRs
  - dependencies
  - scope
  - target area
  - out of scope
  - acceptance criteria
  - stop conditions
  - optional PR context
  - source provenance
- Add builder logic that resolves those fields from a live work item plus optional runtime metadata and PR snapshot inputs.
- Add stable JSON serialization and a deterministic markdown rendering contract suitable for later prompt generation and run-artifact persistence.
- Add targeted tests covering required-field extraction, optional-field absence, and deterministic serialization.

## Out of scope

- Migrating `agent_runtime` prompt builders to consume the bundle
- Refactoring `scripts/invoke.py` or `skills/deliver-wi/SKILL.md`
- Persisting bundle artifacts under `.agent_runtime/`
- Changing governed prompt content or role instructions

## Dependencies

- None. This is the first contract slice for issue `#196`.

## Target area

- `agent_runtime/`
- `agent_runtime/orchestrator/work_item_registry.py` only if a narrow shared extraction helper is required
- `agent_runtime/tests/`

## Acceptance criteria

- One typed handoff-bundle module exists and is importable from repo code that manual and runtime surfaces can both consume later.
- The bundle schema exposes explicit fields or sections for role, work item identity/path, checkout context, linked PRD, linked ADRs, dependencies, scope, target area, out of scope, acceptance criteria, stop conditions, optional PR context, and source provenance.
- The builder accepts a live work item path plus optional runtime/PR inputs and produces deterministic output for identical inputs.
- Stable JSON serialization exists and preserves multiline markdown bullet content without lossy flattening.
- Tests prove extraction of linked PRD, linked ADRs, scope, target area, out-of-scope text, acceptance criteria, stop conditions, and optional PR context handling.
- No runtime prompt builder or manual invocation script is migrated in this slice.

## Test intent

- Add unit tests that construct representative work-item markdown inputs and verify the bundle field mapping exactly.
- Add serialization tests proving repeated renders produce byte-stable JSON for the same logical input.
- Add optional-field tests covering missing linked PRD, missing stop conditions, and absent PR context.

## Stop conditions

- Stop if this slice requires migrating runtime prompt builders or `scripts/invoke.py` to prove correctness.
- Stop if the field set cannot be closed without a new PM decision about role semantics or repo governance.
- Stop if bundle design pressure expands the slice into run-artifact persistence or backend prompt plumbing.

## Review focus

- Contract completeness for the governed handoff field set
- Deterministic serialization and provenance clarity
- Slice discipline: contract and builder only, with no consumer migration hidden inside the PR

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

1. **Linked contract** - No PRD is required; the governing contract is the modernization plan, issue `#196`, and the linked audit.
2. **Scope clarity** - The slice is limited to the shared contract, builder, serialization, and tests.
3. **Dependency clarity** - No upstream implementation dependency must land first.
4. **Target location** - The new shared handoff module and its test area are explicit.
5. **Acceptance clarity** - Required fields, determinism, and non-goals are concrete and reviewable.
6. **Test clarity** - Unit coverage for extraction and serialization is explicit.
7. **Evidence / replay** - The bundle is explicitly shaped for later artifact use without introducing artifact persistence in this slice.
8. **Decision closure** - The role/governance question is bounded to representing existing repo canon, not changing it.
9. **Shared infra** - No shared-infra canon change is required in this contract-first slice.

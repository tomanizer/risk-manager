# WI-MAINT-2B

## Status

**READY** - `WI-MAINT-2A` is merged on `main`, the shared handoff-bundle contract now exists in `agent_runtime/handoff_bundle.py`, and runtime consumer migration is the next bounded slice.

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

Migrate runtime-managed runner execution generation to the shared handoff-bundle contract so PM, coding, review, spec, and issue-planner handoffs stop depending on thin ad hoc prompt assembly.

## Scope

- Update `agent_runtime/orchestrator/execution.py` to build a shared handoff bundle for PM, coding, review, spec, and issue-planner executions.
- Update runtime prompt rendering so those roles consume bundle-derived content rather than bespoke string assembly as the primary context source.
- Persist the serialized handoff bundle in execution metadata or an equivalent canonical execution payload field for later artifact persistence.
- Add or update tests around `build_runner_execution` and role prompt builders to cover the migrated fields.

## Out of scope

- Refactoring `scripts/invoke.py`
- Changing governed system prompt plumbing for automated backends
- Durable run-artifact persistence under `.agent_runtime/`
- Review comment ingestion or CI log ingestion

## Dependencies

- WI-MAINT-2A

## Target area

- `agent_runtime/orchestrator/execution.py`
- `agent_runtime/runners/pm_runner.py`
- `agent_runtime/runners/coding_runner.py`
- `agent_runtime/runners/review_runner.py`
- `agent_runtime/runners/spec_runner.py`
- `agent_runtime/runners/issue_planner_runner.py`
- `agent_runtime/tests/test_transitions.py`
- relevant role-runner tests under `agent_runtime/tests/`

## Acceptance criteria

- `build_runner_execution` constructs a shared handoff bundle for PM, coding, review, spec, and issue-planner executions.
- Runtime prompt rendering for those roles includes the core governed WI contract fields from the shared bundle instead of relying only on thin inline strings.
- Execution metadata carries a serialized bundle payload or an equivalent canonical bundle reference for later run-artifact persistence.
- Tests cover linked PRD propagation, checkout context, optional PR context, acceptance criteria, and stop-condition rendering through runtime execution surfaces.
- No manual invocation surface changes are mixed into this slice.

## Test intent

- Extend transition tests to assert that runtime-built executions carry the shared bundle fields.
- Update role-runner tests to assert rendered prompts include the expected bundle-derived contract sections.
- Keep at least one PM path and one coding/review path under direct assertion so the migrated surface is not partially wired.

## Stop conditions

- Stop if `WI-MAINT-2A` changes the bundle contract materially while this slice is in progress.
- Stop if drift-monitor or PRD-bootstrap handoffs must be migrated to keep this slice coherent; route that as follow-on work instead.
- Stop if the migration requires run-artifact storage or backend-governance changes to land in the same PR.

## Review focus

- Runtime consumption of the shared bundle across all targeted roles
- Elimination of duplicated thin-prompt assembly where the bundle should be authoritative
- Slice discipline: runtime consumer migration only, with no manual-surface or artifact-persistence scope creep

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

1. **Linked contract** - `WI-MAINT-2A` is merged and provides the shared handoff-bundle contract on `main`.
2. **Scope clarity** - Runtime consumer migration only; manual surfaces and backend-governance plumbing remain out of scope.
3. **Dependency clarity** - The bundle contract is stable enough to consume directly.
4. **Target location** - `agent_runtime/orchestrator/`, the role runner modules, and the runtime test files are explicit.
5. **Acceptance clarity** - The targeted roles and fields are concrete and reviewable.
6. **Test clarity** - Transition and role-runner test expectations are explicit.
7. **Evidence / replay** - Serialized bundle payloads are carried forward for later artifact persistence without introducing the artifact subsystem here.
8. **Decision closure** - This slice consumes the established bundle contract rather than designing it.
9. **Shared infra** - No shared-infra canon change is required for this migration slice.

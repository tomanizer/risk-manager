# WI-MAINT-2C

## Status

**BLOCKED** - gated on `WI-MAINT-2A` and `WI-MAINT-2B` merging on `main`.

## Blocker

- The manual invocation surface should not be migrated until the shared handoff-bundle contract exists and the runtime consumer shape is stable enough to compare against.

**Owner:** Coding Agent completes `WI-MAINT-2A` and `WI-MAINT-2B` -> human merge -> PM moves this WI to `ready/`.

## Linked PRD

None - runtime delivery infrastructure maintenance.

Policy basis: [agent_runtime_modernization_plan.md](../../docs/delivery/plans/agent_runtime_modernization_plan.md), [GitHub issue #196](https://github.com/tomanizer/risk-manager/issues/196), [umbrella issue #195](https://github.com/tomanizer/risk-manager/issues/195), and [agent_runtime_audit_2026-04-21.md](../../docs/guides/agent_runtime_audit_2026-04-21.md).

## Linked ADRs

None required.

## Linked shared infra

None.

## Purpose

Migrate the manual invocation tooling to the shared handoff-bundle builder and close the field-parity gap between manual and runtime execution context.

## Scope

- Refactor `scripts/invoke.py` so it resolves work-item, PRD, ADR, and execution-context fields through the shared handoff-bundle builder instead of bespoke WI parsing for fields already represented in the bundle.
- Add tests that compare the core handoff fields produced for the same WI through the manual path and the runtime path.
- Update `skills/deliver-wi/SKILL.md` and `agent_runtime/manual_supervisor_workflow.md` only as needed to keep the operator instructions aligned with the shared handoff model.

## Out of scope

- Changing the manual role-selection policy in `skills/deliver-wi`
- Changing Git freshness or branching policy for manual direct mode
- Adding durable run-artifact persistence
- Changing governed role-instruction content

## Dependencies

- WI-MAINT-2A
- WI-MAINT-2B

## Target area

- `scripts/invoke.py`
- `tests/unit/scripts/`
- `skills/deliver-wi/SKILL.md`
- `agent_runtime/manual_supervisor_workflow.md`

## Acceptance criteria

- `scripts/invoke.py` imports the shared handoff-bundle builder and no longer re-implements the governed WI field extraction that the bundle already owns.
- Manual template filling behavior remains intact for supported roles after the refactor.
- Tests compare the core fields for the same WI across the manual and runtime paths and fail if linked PRD, linked ADRs, scope, target area, out of scope, acceptance criteria, or stop conditions drift.
- Instruction-surface documentation is updated only where needed to reflect the shared handoff model and remains consistent with repo branching rules.

## Test intent

- Add focused script-level tests under `tests/unit/scripts/` for manual bundle use and template-filling parity.
- Add at least one parity test that exercises the same WI through the manual builder and the runtime builder and compares the core governed fields directly.
- Keep role-selection behavior under existing tests or manual expectations; this slice is about context parity, not dispatch policy changes.

## Stop conditions

- Stop if the runtime bundle or prompt rendering contract is still shifting under `WI-MAINT-2B`.
- Stop if manual parity work would require redesigning invocation templates rather than reusing the existing ones.
- Stop if `skills/deliver-wi` would need executable automation behavior changes instead of narrow instruction alignment.

## Review focus

- True field parity between manual and runtime handoff surfaces
- Preservation of current manual template-filling behavior
- Minimal, disciplined instruction-surface edits with no policy drift

## Suggested agent

Coding Agent (after unblock)

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

*Blocked until `WI-MAINT-2A` and `WI-MAINT-2B` complete; when unblocked, all must hold:*

1. **Linked contract** - The shared bundle contract and runtime consumer migration are both merged on `main`.
2. **Scope clarity** - Manual-surface parity only; no template redesign or branching-policy change.
3. **Dependency clarity** - Runtime bundle semantics are stable enough for parity assertions.
4. **Target location** - `scripts/invoke.py`, manual-surface docs, and script tests are explicit.
5. **Acceptance clarity** - The parity fields and preserved behavior are concrete and reviewable.
6. **Test clarity** - Script tests and direct parity assertions are explicit.
7. **Evidence / replay** - This slice improves handoff consistency only; artifact persistence stays out of scope.
8. **Decision closure** - The bundle contract and runtime rendering behavior are already decided upstream.
9. **Shared infra** - No shared-infra canon change is required for this manual-surface parity slice.

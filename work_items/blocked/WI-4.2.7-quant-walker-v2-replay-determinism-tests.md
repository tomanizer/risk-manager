# WI-4.2.7

## Status

**BLOCKED** - sequenced after WI-4.2.6 per PRD-4.2-v2 implementation guidance.

## Blocker

- The replay suite should lock against the telemetry-adopted public Quant Walker v2 implementation on `main`, not an intermediate branch state.

**Owner:** Coding Agent completes WI-4.2.6 -> human merge -> PM moves this WI to `ready/`.

## Linked PRD

`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md`

Public entry point under test: `src/walkers/quant/walker.py` via `from src.walkers.quant import summarize_change`.

## Linked ADRs

- ADR-002
- ADR-003

## Linked shared infra

- `docs/shared_infra/index.md`

## Purpose

Add the focused replay-determinism test suite for Quant Walker v2 so the public `summarize_change` entry point is proven stable across repeated identical invocations over the reachable upstream status surface.

## Scope

- Add replay-style equality tests that invoke `summarize_change` twice with identical arguments and identical fixture-index state and assert equal `QuantInterpretation` outputs.
- Cover the reachable upstream `SummaryStatus` surface on `main`, including representative `OK`, `DEGRADED`, `MISSING_COMPARE`, and `MISSING_HISTORY` outcomes.
- Cover both reachable `INSUFFICIENT_HISTORY` volatility-field paths called out by the PRD.
- Assert `walker_version` is identical across repeated invocations.

## Out of scope

- Any new implementation logic in `src/walkers/quant/` unless a minimal public-surface import fix is strictly required for the test to execute
- Telemetry assertions or adoption-matrix changes
- New fixtures or fixture-index extensions
- Re-testing the full inference-rule matrix already owned by WI-4.2.5

## Dependencies

Blocking:

- WI-4.2.6-quant-walker-v2-telemetry-adoption

Merged prerequisites implied by sequence:

- WI-4.2.5-quant-walker-v2-interpretive-logic

Canon (not WI-gated):

- ADR-002
- ADR-003

## Target area

- `tests/unit/walkers/quant/test_replay_determinism.py`

## Acceptance criteria

- Two identical invocations of `summarize_change` over the same success scenario produce field-for-field equal `QuantInterpretation` outputs.
- The replay suite covers representative reachable scenarios for `OK`, `DEGRADED`, `MISSING_COMPARE`, and `MISSING_HISTORY`.
- The replay suite covers both reachable `INSUFFICIENT_HISTORY` volatility-field paths identified in PRD-4.2-v2.
- `walker_version` is equal across repeated invocations for every tested scenario.
- No new fixture files or fixture-index extensions are introduced.
- No inference-rule behavior changes are mixed into this WI.
- No telemetry assertions are duplicated here.

## Test intent

- For each selected fixture-backed scenario, build or load the existing fixture index once, call `summarize_change` twice with identical inputs, and compare the two `QuantInterpretation` outputs with `==`.
- Keep scenario selection narrow and explicit so reviewers can see which upstream statuses and insufficient-history branches are locked by replay coverage.
- Use the public entry point only; do not test private helpers.

## Review focus

- Replay equality is asserted at the public walker boundary, not only at helper level.
- Scenario coverage matches the PRD-named reachable status surface.
- This WI stays test-only and does not reopen implementation scope.

## Suggested agent

Coding Agent (after unblock)

## READY_CRITERIA (checklist - work_items/READY_CRITERIA.md)

*Blocked until WI-4.2.6 completes; when unblocked, all must hold:*

1. **Linked contract** - PRD-4.2-v2 is merged and the telemetry-adopted v2 Quant Walker implementation is stable on `main`.
2. **Scope clarity** - Replay tests only; no behavior or telemetry changes.
3. **Dependency clarity** - WI-4.2.5 and WI-4.2.6 are merged; public walker behavior is stable.
4. **Target location** - Replay test file under `tests/unit/walkers/quant/` is explicit.
5. **Acceptance clarity** - Repeated-invocation equality cases and required status coverage are concrete.
6. **Test clarity** - Replay-style equality assertions over existing fixtures are explicit.
7. **Evidence / replay** - This WI directly verifies the PRD replay invariant at the walker boundary.
8. **Decision closure** - No unresolved replay-design question remains; the PRD already defines the invariant and coverage intent.
9. **Shared infra** - No shared-infra behavior changes occur in this slice.

## Residual notes for PM / downstream

- This slice closes the remaining replay evidence gap after the public v2 implementation and telemetry are both stable on `main`.
- Keep any future fixture-gap follow-up separate if an unreachable PRD branch is discovered during coding.

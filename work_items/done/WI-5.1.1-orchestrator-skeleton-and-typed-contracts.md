# WI-5.1.1

## Status

**READY** — PRD-5.1 is merged on `main`; all upstream contracts (PRD-1.1-v2, PRD-2.1, PRD-4.1) are implemented and merged.

## Blocker

- None. PM can assign this slice to Coding Agent.

## Linked PRD

docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md

Planned orchestrator package path for this WI is src/orchestrators/daily_risk_investigation/ (plain text only until created on main). Upstream service semantics: [PRD-1.1-v2](docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md), [PRD-2.1](docs/prds/phase-2/PRD-2.1-controls-production-integrity-assessment-service.md). Upstream walker: [PRD-4.1](docs/prds/phase-2/PRD-4.1-data-controller-walker-v1.md).

## Linked ADRs

- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Linked shared infra

- `docs/shared_infra/index.md`
- `docs/shared_infra/telemetry.md`
- `docs/shared_infra/adoption_matrix.md`

## Purpose

First coding slice for the Daily Risk Investigation Orchestrator: create the orchestrator package scaffold under `src/orchestrators/daily_risk_investigation/` (created by this WI), define all typed contracts (`DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, and the four enums), define the `start_daily_run` entry-point signature and `run_id` derivation logic, and add unit tests for contract shapes and `run_id` determinism. No stage execution behavior in this slice.

## Scope

- Create new package `daily_risk_investigation` under `src/orchestrators/` with an `__init__.py` that re-exports only the public surface (`start_daily_run`, `DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, `HandoffStatus`, `TerminalRunStatus`, `ReadinessState`, `OutcomeKind`)
- Define typed models (Pydantic / `StrEnum` per ADR-001):
  - `DailyRunResult` with all fields per PRD-5.1 "Run-level state object"
  - `TargetInvestigationResult` with fields per PRD-5.1 "Per-target investigation object"
  - `TargetHandoffEntry` with fields per PRD-5.1 "Per-target handoff entry"
  - `HandoffStatus` enum with exactly the five values in PRD-5.1
  - `TerminalRunStatus` enum with exactly the five values in PRD-5.1
  - `ReadinessState` enum with exactly the two values (`READY`, `BLOCKED`)
  - `OutcomeKind` enum with exactly the two values (`ASSESSMENT`, `SERVICE_ERROR`)
- Define `start_daily_run` with the exact signature from PRD-5.1 (including `risk_fixture_index` and `controls_fixture_index` optional kwargs); function body raises `NotImplementedError` — no stage implementation yet
- Implement `run_id` derivation (the `"drun_" + sha256(...)` derivation from PRD-5.1 "Run identity") as a private helper; `start_daily_run` must call it so unit tests can verify determinism
- Define `orchestrator_version` as a module-level constant (pinned string, non-empty)
- Update `src/orchestrators/README.md` with a one-line note that `daily_risk_investigation/` is the first implemented orchestrator root (no further scope expansion)
- Unit tests for: all typed contract field shapes, enum vocabularies, `run_id` determinism (equal inputs → equal `run_id`), and a pinned `run_id` hex digest

## Out of scope

- Stage execution (Stages 1–9) — implemented in WI-5.1.2
- Readiness gate, target selection, investigation, challenge gate, synthesis, handoff, persist logic — WI-5.1.2
- Telemetry emission (`emit_operation` calls) — WI-5.1.3
- Adoption matrix flip — WI-5.1.3
- Replay determinism test set — WI-5.1.4
- Materiality logic, second walker, durable persistence, human-in-the-loop challenge, governance approval, UI surface
- Any change to PRD-1.1-v2, PRD-2.1, or PRD-4.1 contracts

## Dependencies

Merged prerequisites:

- PRD-5.1 (docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md) — merged on `main`
- WI-4.1.2-data-controller-walker-delegate-slice (PRD-4.1 implementation)
- WI-2.1.3-integrity-assessment-service (PRD-2.1 implementation)
- WI-1.1.4-risk-summary-core-service (PRD-1.1-v2 implementation)

Canon (not WI-gated):

- ADR-001
- ADR-002
- ADR-003
- ADR-004

## Target area

- New package under src/orchestrators/daily_risk_investigation/ (single module file + `__init__.py`)
- `src/orchestrators/README.md` (one-line update)
- Matching unit tests under tests/unit/orchestrators/daily_risk_investigation/ (created by this WI per repo convention)

## Acceptance criteria

### Functional

- `start_daily_run` is importable as `from src.orchestrators.daily_risk_investigation import start_daily_run` with the exact signature from PRD-5.1 (including `risk_fixture_index` and `controls_fixture_index` optional kwargs)
- Calling `start_daily_run` with valid inputs raises `NotImplementedError` (no stage behavior yet)

### Contract

- `DailyRunResult`, `TargetInvestigationResult`, `TargetHandoffEntry`, `HandoffStatus`, `TerminalRunStatus`, `ReadinessState`, `OutcomeKind` are all importable from the package's public surface
- All enum vocabularies contain exactly the values listed in PRD-5.1; no extra members
- All Pydantic model fields match the field list in PRD-5.1 with correct types and optionality

### Run identity

- `run_id` derivation produces `"drun_" + sha256(...)` per PRD-5.1 "Run identity" normative spec
- Equal inputs produce equal `run_id` across two invocations of the derivation helper
- A unit test pins a known fixed-input set to a known expected hex digest (the exact digest is computed by the coding agent at authoring time and hardcoded as a regression guard)

### Architecture

- Package lives at `src/orchestrators/daily_risk_investigation/` and exposes only the public surface via `__init__.py`
- No imports from `agent_runtime`; no telemetry calls (deferred to WI-5.1.3)
- `src/orchestrators/README.md` reflects that `daily_risk_investigation/` is the first implemented orchestrator root

## Test intent

- **Contract shape tests:** instantiate each Pydantic model with valid kwargs; assert required fields are present and correctly typed
- **Enum vocabulary tests:** assert each enum contains exactly the expected members and no extras
- **`run_id` determinism test:** call the private `run_id` derivation helper twice with identical inputs; assert results are equal strings starting with `"drun_"`
- **Pinned digest test:** fixed known input → assert `run_id == "drun_<expected_hex>"`; the expected hex is hardcoded at authoring time and must not be recomputed at test execution time

## Review focus

- Typed contract completeness against PRD-5.1 field lists
- Enum vocabulary exactness (no extra or missing members)
- `run_id` derivation correctness and determinism
- No stage execution logic in this WI
- No telemetry calls
- Package exports only the public surface

## Suggested agent

Coding Agent

## READY_CRITERIA (checklist — work_items/READY_CRITERIA.md)

1. **Linked contract** — PRD-5.1 exists on `main` and is linked above.
2. **Scope clarity** — Typed contracts + `run_id` derivation + `start_daily_run` stub + unit tests only.
3. **Dependency clarity** — All upstream PRDs and walker implementations are merged; no unresolved upstream contract.
4. **Target location** — `src/orchestrators/daily_risk_investigation/`, `src/orchestrators/README.md`, `tests/unit/orchestrators/daily_risk_investigation/`.
5. **Acceptance clarity** — All criteria are explicit, reviewable, and directly derived from PRD-5.1.
6. **Test clarity** — Unit tests: contract shapes, enum vocabularies, `run_id` determinism, pinned digest.
7. **Evidence / replay** — No replay state changes in this WI; `run_id` derivation is tested for determinism.
8. **Decision closure** — No unresolved architecture decisions for v1 skeleton; all ADRs linked.
9. **Shared infra** — Telemetry is declared out of scope for this slice; adoption matrix is not updated (remains `planned` until WI-5.1.3).

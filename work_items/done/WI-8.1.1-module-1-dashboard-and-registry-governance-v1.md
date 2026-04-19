# WI-8.1.1

## Status

**DONE**

## Linked PRD

docs/prds/phase-8/PRD-8.1-module-dashboard-and-registry-governance-v1.md

## Linked ADRs

- ADR-001
- ADR-002

## Linked shared / delivery canon

- `docs/roadmap/phased_implementation_roadmap.md`
- `docs/registry/current_state_registry.yaml`
- `docs/delivery/01_pm_operating_model.md`
- `docs/delivery/05_repo_drift_monitoring.md`

## Purpose

First bounded slice for registry-backed module dashboards: extend the current-state registry with Module 1 dashboard fields, add a generator script, generate the Module 1 dashboard page under `docs/roadmap/`, and wire PM / review / drift-monitor instructions so the new status surface is governed rather than ad hoc.

## Scope

- Extend `docs/registry/current_state_registry.yaml` with:
  - `module_dashboards`
  - richer capability-level fields needed for Module 1 MVP tracking and PRD lineage
- Add `scripts/render_module_dashboard.py`
- Generate `docs/roadmap/module_1_var_dashboard.md` from registry state
- Update PM / review / drift-monitor instruction and delivery canon surfaces so:
  - PM owns registry-backed dashboard freshness
  - review checks status-surface freshness when maturity/lineage changes
  - drift-monitor treats generated module dashboard pages as governed status surfaces
- Add unit tests for the renderer

## Out of scope

- dashboards for modules beyond Module 1
- a web UI or external dashboard application
- CI enforcement for dashboard regeneration
- a full registry schema validator
- any new product functionality under `src/`

## Target area

- `docs/registry/current_state_registry.yaml`
- `docs/roadmap/module_1_var_dashboard.md`
- `scripts/render_module_dashboard.py`
- `tests/unit/scripts/test_render_module_dashboard.py`
- `docs/delivery/01_pm_operating_model.md`
- `docs/delivery/05_repo_drift_monitoring.md`
- `prompts/agents/pm_agent_instruction.md`
- `prompts/agents/review_agent_instruction.md`
- `prompts/agents/drift_monitor_agent_instruction.md`

## Acceptance criteria

1. Module 1 dashboard page exists under `docs/roadmap/` and is generated from registry state
2. The dashboard clearly states:
   - what is implemented
   - what is missing for MVP
   - which PRDs are missing
   - which existing PRDs require a new version
3. Renderer unit tests pass
4. Existing registry-alignment and instruction-surface tests still pass
5. PM / review / drift-monitor surfaces all mention the new dashboard governance responsibilities explicitly

## Verification

- `python scripts/render_module_dashboard.py --module-id MODULE-1-VAR`
- `pytest -q tests/unit/scripts/test_render_module_dashboard.py`
- `pytest -q tests/unit/scripts/test_render_module_dashboard.py tests/unit/agent_runtime/test_registry_alignment.py tests/unit/agent_runtime/test_instruction_surfaces.py`

## Notes

- This WI records the governance trail for the initial Module 1 dashboard implementation already landed in the repository.
- Future expansion to additional modules, CI enforcement, or dedicated dashboard drift scanning should be tracked as follow-on WIs under PRD-8.1 or its successor.

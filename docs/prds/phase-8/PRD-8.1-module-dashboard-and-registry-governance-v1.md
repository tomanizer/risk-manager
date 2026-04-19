# PRD-8.1: Module Dashboard And Registry Governance v1

## Header

- **PRD ID:** PRD-8.1
- **Title:** Module Dashboard And Registry Governance v1
- **Phase:** Phase 8
- **Status:** Implemented — WI-8.1.1 DONE; dashboard live on main as of 2026-04-19
- **Layer:** Delivery governance / shared status surfaces
- **Type:** Registry-backed documentation and workflow governance
- **Primary owner:** PM / Coordination Agent
- **Supporting owners:** Review Agent, Drift Monitor Agent, Repository Maintenance
- **Related canon:** `docs/roadmap/phased_implementation_roadmap.md`, `docs/registry/current_state_registry.yaml`, `docs/delivery/01_pm_operating_model.md`, `docs/delivery/05_repo_drift_monitoring.md`
- **Related implementation surfaces:** `scripts/render_module_dashboard.py`, `docs/roadmap/`

## Purpose

Provide a governed, human-readable module dashboard that shows where a module stands at any point in delivery, what is implemented, what is missing for MVP, which PRDs are missing, and which existing PRDs require a new version.

v1 establishes the pattern for Module 1 only, using the registry as the canonical source of truth and a generated Markdown page under `docs/roadmap/` as the operator-facing surface.

## Why this exists

The repository already has:

- a phase roadmap
- a current-state registry
- work-item state
- PRD lineage spread across multiple directories

Those surfaces are useful but not sufficient to answer one operator question cleanly:

> For this module, what is implemented now, what is missing for MVP, and what contracts are still needed?

Without a governed dashboard, the answer lives across PRDs, work items, catalogs, registry entries, and implementation state. That raises PM routing risk and makes drift harder to detect.

## Supported process context

This PRD supports:

- PM readiness and sequencing
- post-merge status updates
- review of capability-maturity changes
- drift monitoring of roadmap/registry/implementation alignment

It does not support:

- product planning outside the repository
- UI productization of dashboards
- automated merge decisions

## Human owner and decision boundary

- **Primary human-facing owner:** PM / Coordination Agent
- **Accountable human boundary:** repository operator / maintainer decides whether dashboard state is accurate enough to treat as current governance truth

Agents may update registry-backed status surfaces only when the implementation or canon change materially affects module maturity, MVP blockers, or PRD lineage.

## In scope

- one registry-backed module dashboard for Module 1
- canonical status data stored in `docs/registry/current_state_registry.yaml`
- one generated Markdown page under `docs/roadmap/`
- a render script that converts registry dashboard entries into Markdown
- explicit Module 1 fields for:
  - mission
  - MVP definition
  - current overall status
  - capability status
  - MVP blockers
  - PRD lineage
  - next recommended slices
  - post-MVP enhancements
- workflow hooks requiring PM, review, and drift-monitor surfaces to keep the dashboard current

## Out of scope

- dashboards for modules other than Module 1
- a web UI, terminal UI, or external dashboard application
- automatic status inference from code alone
- replacing PRDs, work items, or the current-state registry with the dashboard
- a full schema validator for every registry field in v1
- GitHub Project / Notion / Airtable synchronization

## Core principles

- registry is canonical, dashboard is derived
- generated Markdown is human-facing, reviewable, and linkable
- MVP status must be explicit per module
- missing PRDs and PRD-version gaps must be called out directly
- PM owns status truth, but review and drift-monitor surfaces enforce freshness
- the dashboard must reduce planning ambiguity, not add another disconnected planning layer

## Canonical surfaces

### Source of truth

`docs/registry/current_state_registry.yaml`

The registry remains the authoritative structured source for:

- module dashboard state
- capability-level maturity
- missing-for-MVP items
- PRD lineage
- version-gap tracking

### Generated human-facing surface

`docs/roadmap/module_1_var_dashboard.md`

This file is generated from registry state and should not be hand-edited.

### Generator

`scripts/render_module_dashboard.py`

The renderer reads the registry and writes the generated dashboard page.

## Required dashboard sections (v1)

The generated page must contain:

- mission
- MVP definition
- current overall status
- journey/status stages
- capability status table
- MVP gap summary
- PRD lineage table
- in-progress items
- next recommended slices
- post-MVP enhancements
- open questions
- change log

## Required registry fields (v1)

The registry must support a `module_dashboards` section with fields sufficient to render the required dashboard sections.

At minimum the v1 dashboard entry must support:

- `id`
- `name`
- `owner_role`
- `dashboard_path`
- `overall_state`
- `delivery_phase`
- `mission`
- `mvp_definition`
- `summary`
- `current_mvp_blockers`
- `not_required_for_mvp`
- `journey_stages`
- `capabilities`
- `prd_lineage`
- `in_progress_items`
- `next_recommended_slices`
- `post_mvp_enhancements`
- `open_questions`
- `change_log`

Capability entries must support, at minimum:

- `component_ref` or `name`
- `layer`
- `current_state`
- `implemented_now`
- `missing_for_mvp`
- `missing_prds`
- `needs_new_prd_version`
- `next_version_reason`
- `next_slice`

## Workflow responsibilities

### PM

PM must update the registry and regenerate the affected dashboard when:

- a capability maturity state changes
- an MVP blocker is removed or newly discovered
- PRD lineage changes
- a new PRD or PRD v2 becomes required

### Review

Review must check status-surface freshness when a PR changes capability maturity, MVP blockers, or PRD lineage.

### Drift monitor

Drift monitor must treat generated dashboard pages as governed status surfaces and flag mismatches between:

- registry state
- generated dashboard content
- implemented repository reality
- PRD/work-item status claims

## Degraded and drift states

The dashboard system is degraded when:

- the registry exists but the dashboard has not been regenerated after a material state change
- the generated dashboard page contradicts implementation or PRD reality
- a capability is marked mature but the required PRD or implementation is missing

These are governance failures, not UI issues. They must be routed primarily to PM, and to PRD/spec when lineage is wrong or incomplete.

## Acceptance criteria

### Functional

- Module 1 dashboard page exists under `docs/roadmap/`
- dashboard content is generated from the registry, not hand-maintained prose
- Module 1 dashboard clearly states:
  - what is implemented
  - what is missing for MVP
  - which PRDs are missing
  - which PRDs need a new version

### Workflow

- PM instruction surfaces explicitly reference registry-backed module dashboard maintenance
- Review instruction surfaces explicitly check status-surface freshness
- Drift-monitor instruction surfaces explicitly treat module dashboards as governed status surfaces

### Test

- unit tests cover rendering of the dashboard from a registry fixture
- unit tests verify the renderer CLI writes the expected page
- existing registry-alignment and instruction-surface checks continue to pass

## Test intent

- render a minimal registry fixture and assert required dashboard sections are present
- assert known capability and PRD-lineage values appear in the generated output
- assert the CLI writes the configured dashboard path
- run instruction-surface and registry-alignment tests to confirm the new governance surfaces do not break existing drift controls

## Suggested implementation decomposition

v1 is intentionally one bounded slice:

1. extend the registry schema in place
2. add the renderer
3. seed the Module 1 dashboard entry
4. generate the dashboard page
5. update PM / review / drift-monitor workflow hooks
6. add renderer tests

Future slices, if needed, should be separate:

- dashboard schema validation
- additional module dashboards
- CI enforcement for dashboard regeneration
- richer drift scanning for dashboard/registry mismatches

## Open questions

- should generated module dashboards eventually be re-rendered in CI and checked for clean diff?
- should a dedicated deterministic drift scanner compare dashboard contents to registry contents, or is registry plus review discipline sufficient in v1?
- when the second module dashboard is added, should there be an index page under `docs/roadmap/`?

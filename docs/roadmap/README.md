# Roadmap Surfaces

## Purpose

This folder holds operator-facing roadmap views for repository delivery state.

Use these surfaces together:

- [Phased Implementation Roadmap](/Users/thomas/Documents/Projects/risk-manager/docs/roadmap/phased_implementation_roadmap.md:1)
  High-level phase sequencing and delivery principles for the repository as a whole.
- [Module 1 Dashboard: End-to-End VaR Workflow](/Users/thomas/Documents/Projects/risk-manager/docs/roadmap/module_1_var_dashboard.md:1)
  Registry-backed status view for Module 1 showing what is implemented, what is missing for MVP, which PRDs are missing, and which capabilities need a new PRD version.

## Source Of Truth

- Phase-level sequencing remains governed by [phased_implementation_roadmap.md](/Users/thomas/Documents/Projects/risk-manager/docs/roadmap/phased_implementation_roadmap.md:1).
- Module dashboard content is generated from [current_state_registry.yaml](/Users/thomas/Documents/Projects/risk-manager/docs/registry/current_state_registry.yaml:1) via [render_module_dashboard.py](/Users/thomas/Documents/Projects/risk-manager/scripts/render_module_dashboard.py:1).

Do not hand-edit generated dashboard pages. Update the registry and re-render instead.

## Ownership

- PM / Coordination Agent owns freshness of module dashboard state.
- Review Agent checks status-surface freshness when capability maturity or PRD lineage changes.
- Drift Monitor Agent audits roadmap / registry / implementation alignment.

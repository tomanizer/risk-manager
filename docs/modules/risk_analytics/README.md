# Risk Analytics Module Documentation Pack

## Purpose

This folder captures the missing detailed design work for the first implementation module.

It turns conversation design into repo canon so that coding agents, reviewers, and human owners can work from stable artifacts rather than chat history.

## Contents

- `01_capability_overview.md`
- `02_service_contracts.md`
- `03_data_structures.md`
- `04_flows_and_graphs.md`
- `05_work_item_map.md`

## Scope

This pack covers the first deterministic module slice centred on the Risk Summary Service and its immediate dependencies:

- canonical risk summary retrieval
- hierarchy and scope semantics
- first-order delta versus second-order volatility-aware change
- replay and business-day behavior
- implementation decomposition

## Relationship to PRDs

These documents complement:

- `docs/prds/phase-1/PRD-1.1-risk-summary-service.md`
- `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`

The PRDs define the product requirement and implementation boundary.

This pack adds the richer design explanation, contracts, graphs, and implementation detail that were developed in conversation but not yet captured properly in the repo.

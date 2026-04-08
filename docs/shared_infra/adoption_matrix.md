# Shared Infrastructure Adoption Matrix

## Purpose

Track shared-infrastructure usage, owners, and rollout state by layer.

## Status legend

- `adopted`: uses shared infrastructure contract directly
- `partial`: mixed usage, migration in progress
- `planned`: not yet adopted, tracked by work item

## Matrix

| Area | Shared infra item | Status | Notes |
| --- | --- | --- | --- |
| `src/modules/controls_integrity/` | shared evidence contract (`EvidenceRef` in `src/shared/evidence.py`) | adopted | Module imports canonical type from `src.shared`; re-exported via `controls_integrity.contracts` for stable public API (WI-2.1.6) |
| `src/modules/risk_analytics/` | telemetry contract | planned | No module-local telemetry helper exists under `src/` today; adoption pending tracked implementation work items against `docs/shared_infra/telemetry.md` |
| `src/walkers/` | telemetry contract | planned | Enforce once first walker telemetry WI lands |
| `src/orchestrators/` | telemetry contract | planned | Keep orchestration concerns separate from deterministic services |
| `agent_runtime/` | telemetry framework | adopted | Canonical runtime implementation; design reference only for `src/` |

## Governance

- PM validates matrix updates for cross-cutting infra WIs.
- Review agent flags matrix drift when PR changes shared infra behavior without matrix updates.

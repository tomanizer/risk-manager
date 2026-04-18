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
| `src/modules/risk_analytics/` | telemetry contract | adopted | Uses `src.shared.telemetry.emit_operation` (and shared helpers) for PRD minimum operation logs per WI-1.1.11; no module-local duplicate status mapping |
| `src/walkers/` | telemetry contract | adopted | `data_controller` walker emits via `src.shared.telemetry.emit_operation` (WI-4.1.4) |
| `src/orchestrators/` | telemetry contract | planned | Keep orchestration concerns separate from deterministic services |
| `agent_runtime/` | telemetry framework | adopted | Canonical runtime implementation; design reference only for `src/` |

## Governance

- PM validates matrix updates for cross-cutting infra WIs.
- Review agent flags matrix drift when PR changes shared infra behavior without matrix updates.

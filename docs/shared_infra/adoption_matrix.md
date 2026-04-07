# Shared Infrastructure Adoption Matrix

## Purpose

Track shared-infrastructure usage, owners, and rollout state by layer.

## Status legend

- `adopted`: uses shared infrastructure contract directly
- `partial`: mixed usage, migration in progress
- `planned`: not yet adopted, tracked by work item

## Matrix

| Area | Shared infra item | Status | Notes |
|---|---|---|---|
| `src/modules/risk_analytics/` | telemetry contract | partial | Local `operation_logging.py` aligned to contract; candidate to move under `src/shared/telemetry/` |
| `src/walkers/` | telemetry contract | planned | Enforce once first walker telemetry WI lands |
| `src/orchestrators/` | telemetry contract | planned | Keep orchestration concerns separate from deterministic services |
| `agent_runtime/` | telemetry framework | adopted | Canonical runtime implementation; design reference only for `src/` |

## Governance

- PM validates matrix updates for cross-cutting infra WIs.
- Review agent flags matrix drift when PR changes shared infra behavior without matrix updates.


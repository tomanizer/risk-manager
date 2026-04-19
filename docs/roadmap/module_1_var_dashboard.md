<!-- GENERATED FILE: edit docs/registry/current_state_registry.yaml and rerun scripts/render_module_dashboard.py -->

# Module 1 Dashboard: End-to-End VaR Workflow

_Last updated: 2026-04-19_  
_Source of truth: `docs/registry/current_state_registry.yaml`_  
_Owner: PM / Coordination Agent_

## Mission

Deliver a replayable, deterministic, explainable daily VaR investigation workflow for Module 1 using governed deterministic services, specialist walkers, and bounded orchestration.

## MVP Definition

- deterministic VaR retrieval and change-profile analysis
- trust / readiness assessment
- quantitative interpretation
- time-series interpretation
- orchestrated investigation flow
- governance-ready handoff output

## Current Overall Status

- Overall state: `MVP_PARTIAL`
- Delivery phase: `Phase 5`
- Summary: Deterministic risk analytics and controls-integrity foundations are implemented. The bounded daily orchestrator exists. Multi-walker analytical interpretation and governance-ready output are still missing.
- Current MVP blockers:
  - Quant Walker v2 contract is not yet defined.
  - Time Series Walker v1 PRD is missing.
  - Daily Risk Investigation Orchestrator v2 multi-walker routing is missing.
  - Governance / Reporting Walker v1 PRD is missing.

## Journey Status

| Stage | Goal | Status | Notes |
| --- | --- | --- | --- |
| Deterministic foundation | canonical deterministic VaR analytics | `done` | Risk Analytics and Controls Integrity deterministic services are implemented. |
| Trust / controls gate | determine whether data is safe to interpret | `done` | Data Controller Walker and bounded trust-gate orchestration exist. |
| Analytical interpretation | explain quantitative movement and historical context | `partial` | Quant Walker exists as a delegate only; Time Series Walker is missing. |
| Workflow orchestration | route, synthesize, challenge, and hand off the investigation | `partial` | Daily orchestrator exists but is single-walker only. |
| Governance-ready handoff | produce management-ready conclusions and actions | `not_started` | Governance / Reporting Walker is not implemented. |
| Production operation | durable, repeatable, live execution | `not_started` | Durable persistence and live execution contracts are not yet implemented. |

## Capability Status

| Capability | Layer | Current State | Implemented Now | Missing For MVP | Missing PRD | Needs New PRD Version? | Reason | Next Slice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Risk Analytics | module | `implemented` | get_risk_summary<br>get_risk_delta<br>get_risk_history<br>get_risk_change_profile<br>fixture loader and business-day resolver | Decide whether production data integration is inside MVP scope. | none | `no` | none | Decide whether a production adapter PRD is required for MVP. |
| Controls Integrity | module | `implemented` | IntegrityAssessment service<br>shared evidence refs<br>replay and validation coverage | none | none | `no` | none | No immediate MVP gap; extend only if new control families are required. |
| Data Controller Walker | walker | `implemented` | assess_integrity delegate<br>walker telemetry | none | none | `no` | none | Keep stable unless downstream consumers require richer walker-owned output. |
| Quant Walker | walker | `delegate_only` | summarize_change delegate over get_risk_change_profile | interpretive quantitative walker output | none | `yes` | Current PRD covers delegation-only v1. Module 1 MVP needs actual walker inference over deterministic risk change output. | Author PRD-4.2-v2 for interpretive Quant Walker output. |
| Time Series Walker | walker | `not_started` | none | full time-series interpretation capability | PRD-TBD-Time-Series-Walker-v1 | `yes` | Capability has no v1 implementation PRD yet. | Author Time Series Walker v1 PRD. |
| Daily Risk Investigation | orchestrator | `partial` | bounded single-walker daily run<br>target selection<br>challenge gate<br>typed handoff<br>shared telemetry | multi-walker routing<br>multi-walker synthesis<br>governance-ready downstream path | none | `yes` | PRD-5.1 intentionally excludes quant/time-series routing and richer orchestration behavior required for Module 1 MVP. | Author PRD-5.1-v2 for multi-walker orchestration. |
| Governance / Reporting Walker | walker | `not_started` | none | governance-ready output | PRD-TBD-Governance-Reporting-Walker-v1 | `yes` | Capability has no v1 implementation PRD yet. | Author Governance / Reporting Walker v1 PRD. |
| Production integration | cross-cutting | `not_started` | none | explicit live execution / persistence decision | PRD-TBD-Module-1-Production-Integration | `yes` | Module 1 does not yet define whether MVP is fixture-backed only or requires live execution semantics. | Decide whether production integration is inside or after MVP, then author the required PRD. |

## MVP Gap Summary

The following items are still required to declare Module 1 MVP complete:

- Quant Walker v2 contract is not yet defined.
- Time Series Walker v1 PRD is missing.
- Daily Risk Investigation Orchestrator v2 multi-walker routing is missing.
- Governance / Reporting Walker v1 PRD is missing.

The following items are explicitly not required for Module 1 MVP:

- Market Context Walker
- Critic / Challenge Walker
- Human workflow / UX layer
- Advanced production scheduling

## PRD Lineage

| Capability | Active PRD | Status | Supersedes | Next Needed PRD | Why |
| --- | --- | --- | --- | --- | --- |
| Risk Analytics | PRD-1.1-v2 | `active` | PRD-1.1-v1 | none | Current deterministic bounded scope is stable. |
| Controls Integrity | PRD-2.1 | `active` | none | none | Current bounded trust-assessment scope is stable. |
| Data Controller Walker | PRD-4.1 | `active` | none | none | v1 delegate is sufficient for the current trust-gate role. |
| Quant Walker | PRD-4.2 | `active` | none | PRD-4.2-v2 | v1 is delegation-only; Module 1 MVP needs interpretive walker output. |
| Time Series Walker | none | `missing` | none | PRD-TBD-Time-Series-Walker-v1 | Capability required for MVP but no implementation PRD exists. |
| Daily Risk Investigation Orchestrator | PRD-5.1 | `active` | none | PRD-5.1-v2 | Current orchestrator is bounded to a single-walker flow. |
| Governance / Reporting Walker | none | `missing` | none | PRD-TBD-Governance-Reporting-Walker-v1 | Capability required for MVP but no implementation PRD exists. |

## In Progress

None recorded.

## Next Recommended Slices

1. Author PRD-4.2-v2 for interpretive Quant Walker output.
2. Author Time Series Walker v1 PRD.
3. Author PRD-5.1-v2 for multi-walker orchestration.
4. Author Governance / Reporting Walker v1 PRD.

## Post-MVP Enhancements

- Market Context Walker
- Critic / Challenge Walker
- Human workflow and UX layer
- richer production operations

## Open Questions

- Is live-data integration inside Module 1 MVP or immediately post-MVP?
- Is Governance / Reporting Walker required for MVP or can typed handoff suffice?

## Change Log

- 2026-04-19: Initial Module 1 dashboard seed added to the registry.

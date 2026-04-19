<!-- GENERATED FILE: edit docs/registry/current_state_registry.yaml and rerun scripts/render_module_dashboard.py -->

# Module 1 Dashboard: End-to-End VaR Workflow

_Last updated: 2026-04-20_  
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
- Summary: Deterministic risk analytics and controls-integrity foundations are implemented. The bounded daily orchestrator exists. PRD-4.2-v2 contracts interpretive Quant Walker output; typed-contract and inference implementation (WI-4.2.4–4.2.7) is still outstanding. Multi-walker orchestration and governance-ready narrative output beyond typed handoff are still missing.
- Current MVP blockers:
  - Quant Walker v2 interpretive implementation (PRD-4.2-v2; WI-4.2.4–4.2.7) is not yet on main.
  - Time Series Walker v1 implementation (PRD-4.3; WI-4.3.1–WI-4.3.4) is not yet on main.
  - Daily Risk Investigation Orchestrator v2 multi-walker routing is missing.

## Journey Status

| Stage | Goal | Status | Notes |
| --- | --- | --- | --- |
| Deterministic foundation | canonical deterministic VaR analytics | `done` | Risk Analytics and Controls Integrity deterministic services are implemented. |
| Trust / controls gate | determine whether data is safe to interpret | `done` | Data Controller Walker and bounded trust-gate orchestration exist. |
| Analytical interpretation | explain quantitative movement and historical context | `partial` | Quant Walker remains delegate-only in code; PRD-4.2-v2 defines interpretive output — implementation pending. Time Series Walker v1 is specified by PRD-4.3; implementation is not yet on main. |
| Workflow orchestration | route, synthesize, challenge, and hand off the investigation | `partial` | Daily orchestrator exists but is single-walker only. |
| Governance-ready handoff | produce management-ready conclusions and actions | `not_started` | Governance / Reporting Walker is not implemented. |
| Production operation | durable, repeatable, live execution | `not_started` | Durable persistence and live execution contracts are not yet implemented. |

## Capability Status

| Capability | Layer | Current State | Implemented Now | Missing For MVP | Missing PRD | Needs New PRD Version? | Reason | Next Slice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Risk Analytics | module | `implemented` | get_risk_summary<br>get_risk_delta<br>get_risk_history<br>get_risk_change_profile<br>fixture loader and business-day resolver | none | none | `no` | none | No MVP gap. Production data integration is post-MVP (PM decision 2026-04-19 — DECISION-MVP-01). |
| Controls Integrity | module | `implemented` | IntegrityAssessment service<br>shared evidence refs<br>replay and validation coverage | none | none | `no` | none | No immediate MVP gap; extend only if new control families are required. |
| Data Controller Walker | walker | `implemented` | assess_integrity delegate<br>walker telemetry | none | none | `no` | none | Keep stable unless downstream consumers require richer walker-owned output. |
| Quant Walker | walker | `delegate_only` | summarize_change delegate over get_risk_change_profile | interpretive quantitative walker output | none | `no` | PRD-4.2-v2 is merged; remaining gap is implementation per WI-4.2.4–4.2.7. | Deliver WI-4.2.4–4.2.7 (typed contracts, inference, telemetry, replay tests) per PRD-4.2-v2. |
| Time Series Walker | walker | `not_started` | none | full time-series interpretation capability | none | `no` | PRD-4.3 is the v1 contract; implementation (WI-4.3.1–WI-4.3.4) is not yet on main. | Deliver WI-4.3.1–WI-4.3.4 per PRD-4.3. |
| Daily Risk Investigation | orchestrator | `partial` | bounded single-walker daily run<br>target selection<br>challenge gate<br>typed handoff<br>shared telemetry | multi-walker routing<br>multi-walker synthesis<br>governance-ready downstream path | none | `yes` | PRD-5.1 intentionally excludes quant/time-series routing and richer orchestration behavior required for Module 1 MVP. | Author PRD-5.1-v2 for multi-walker orchestration. |
| Governance / Reporting Walker | walker | `not_started` | none | none | PRD-TBD-Governance-Reporting-Walker-v1 | `yes` | Post-MVP (PM decision 2026-04-19). Typed DailyRunResult handoff is sufficient for MVP. Governance Walker input types depend on Quant Walker v2 and Time Series Walker v1 typed outputs; both are specified (PRD-4.2-v2, PRD-4.3) but interpretive implementations are not yet on main. | Post-MVP (near-term) — author Governance / Reporting Walker v1 PRD once interpretive outputs from Quant (WI-4.2.4–4.2.7) and Time Series (WI-4.3.x) are available for handoff design. |
| Production integration | cross-cutting | `not_started` | none | none | PRD-TBD-Module-1-Production-Integration | `yes` | Post-MVP (PM decision 2026-04-19). MVP is fixture-backed and operator-invoked. Live-data integration and database persistence are a near-term post-MVP priority. | Post-MVP — author production integration PRD after Module 1 analytical interpretation implementations land (Quant WI-4.2.4–4.2.7 per PRD-4.2-v2; Time Series WI-4.3.x per PRD-4.3). |

## MVP Gap Summary

The following items are still required to declare Module 1 MVP complete:

- Quant Walker v2 interpretive implementation (PRD-4.2-v2; WI-4.2.4–4.2.7) is not yet on main.
- Time Series Walker v1 implementation (PRD-4.3; WI-4.3.1–WI-4.3.4) is not yet on main.
- Daily Risk Investigation Orchestrator v2 multi-walker routing is missing.

The following items are explicitly not required for Module 1 MVP:

- Market Context Walker
- Critic / Challenge Walker
- Human workflow / UX layer
- Advanced production scheduling
- Live-data integration and production database adapter (PM decision 2026-04-19 — post-MVP; near-term priority)
- Governance / Reporting Walker v1 (PM decision 2026-04-19 — typed handoff sufficient for MVP; near-term post-MVP)

## PRD Lineage

| Capability | Active PRD | Status | Supersedes | Next Needed PRD | Why |
| --- | --- | --- | --- | --- | --- |
| Risk Analytics | PRD-1.1-v2 | `active` | PRD-1.1-v1 | none | Current deterministic bounded scope is stable. |
| Controls Integrity | PRD-2.1 | `active` | none | none | Current bounded trust-assessment scope is stable. |
| Data Controller Walker | PRD-4.1 | `active` | none | none | v1 delegate is sufficient for the current trust-gate role. |
| Quant Walker | PRD-4.2-v2 | `active` | PRD-4.2-v1 | none | v2 defines interpretive QuantInterpretation output; v1 is archived. Module 1 MVP still needs the WI-4.2.4–4.2.7 implementation on main. |
| Time Series Walker | PRD-4.3 | `active` | none | none | v1 contract is PRD-4.3; implementation (WI-4.3.x) is outstanding on main. |
| Daily Risk Investigation Orchestrator | PRD-5.1 | `active` | none | PRD-5.1-v2 | Current orchestrator is bounded to a single-walker flow. |
| Governance / Reporting Walker | none | `missing` | none | PRD-TBD-Governance-Reporting-Walker-v1 | Post-MVP (near-term). Typed handoff sufficient for MVP per PM decision 2026-04-19; PRD to be authored after interpretive outputs exist on main (PRD-4.2-v2 Quant, PRD-4.3 Time Series). |

## In Progress

None recorded.

## Next Recommended Slices

1. Deliver WI-5.1.4 (replay determinism tests) — Coding Agent, no blockers.
2. Deliver WI-4.2.4–4.2.7 (Quant Walker v2 implementation per PRD-4.2-v2) — Coding Agent / Issue Planner.
3. Deliver WI-4.3.1–WI-4.3.4 per PRD-4.3 (Time Series Walker v1) — Coding Agent / Issue Planner.
4. Author PRD-5.1-v2 for multi-walker orchestration — PRD / Spec Author (after Quant Walker v2 typed output is contracted per PRD-4.2-v2).
5. [Post-MVP] Author Governance / Reporting Walker v1 PRD after interpretive implementations land (PRD-4.2-v2 Quant, PRD-4.3 Time Series).
6. [Post-MVP near-term priority] Author production integration PRD for live-data and database persistence.

## Post-MVP Enhancements

- Live-data integration and production database adapter (near-term priority — see closed decision DECISION-MVP-01)
- Governance / Reporting Walker v1 (near-term — see closed decision DECISION-MVP-02)
- Market Context Walker
- Critic / Challenge Walker
- Human workflow and UX layer
- richer production operations and scheduling

## Open Questions

None — all open questions have been closed.

## Closed Decisions

### DECISION-MVP-01 — 2026-04-19

**Question:** Is live-data integration inside Module 1 MVP or immediately post-MVP?

**Decision:** Post-MVP. MVP is fixture-backed, operator-invoked execution only. Live-data integration and database persistence are explicitly deferred to the post-MVP production operations stage.

**Rationale:** Narrowest path consistent with ADR-002 replay-first discipline. The Module 1 analytical interpretation layer (Quant Walker v2 per PRD-4.2-v2; Time Series Walker v1) can be fully delivered without a live-data adapter.

**Note:** Live-data and database persistence must be implemented as a near-term post-MVP priority. Do not delay this indefinitely after MVP closes.

### DECISION-MVP-02 — 2026-04-19

**Question:** Is Governance / Reporting Walker required for MVP or can typed handoff suffice?

**Decision:** Typed handoff is sufficient for MVP. The DailyRunResult with TargetHandoffEntry objects (handoff_status, blocking_reason_codes, cautionary_reason_codes) constitutes a machine-readable governance-ready handoff. Governance / Reporting Walker is deferred to near-term post-MVP.

**Rationale:** Governance Walker input types depend on Quant Walker v2 and Time Series Walker v1 typed outputs. Both contracts exist (PRD-4.2-v2, PRD-4.3), but neither interpretive implementation is on main yet. Authoring Governance Walker PRD before those surfaces are exercised in code would still require guessing integration details.

**Note:** Governance / Reporting Walker v1 PRD should be authored once Quant and Time Series interpretive outputs are available on main for handoff design, not only after all downstream consumers exist.

## Change Log

- 2026-04-19: Initial Module 1 dashboard seed added to the registry.
- 2026-04-19: PM decision DECISION-MVP-01 — MVP is fixture-backed only; live-data is post-MVP near-term priority.
- 2026-04-19: PM decision DECISION-MVP-02 — typed handoff sufficient for MVP; Governance Walker deferred to near-term post-MVP.
- 2026-04-20: Quant Walker lineage — active PRD PRD-4.2-v2 (supersedes PRD-4.2-v1); MVP blockers and slices updated for merged contract vs implementation gap.
- 2026-04-20: Time Series Walker v1 contract recorded as PRD-4.3; registry lineage replaces PRD-TBD-Time-Series-Walker-v1; dashboard regenerated.

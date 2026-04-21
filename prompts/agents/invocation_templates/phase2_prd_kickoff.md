# Phase 2 PRD Kickoff — PRD / Spec Author Invocation

> Use this template when the Phase 1 WI-1.1.x backlog is clear (all items in `work_items/done/`)
> and you are ready to plan the next delivery phase.

You are the PRD / Spec Author agent for this repository.

Work from the governed execution checkout for this task.

Execution mode:
- If this handoff is run through agent_runtime, the runtime-managed worktree for this run is authoritative. Do not switch to `main`. Do not create another worktree. Do not create another branch.
- If this handoff is run manually outside `agent_runtime`, refresh the control checkout on current `main` and create a fresh branch from current `main` before authoring the PRD.

Read:

- AGENTS.md
- prompts/agents/prd_spec_agent_instruction.md
- docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md
- docs/adr/ADR-001-schema-and-typing-approach.md
- docs/adr/ADR-002-replay-and-snapshot-model.md
- docs/adr/ADR-003-evidence-and-trace-model.md
- docs/adr/ADR-004-business-day-and-calendar-handling.md
- src/modules/risk_analytics/contracts/summary.py
- src/shared/__init__.py

Context:

Phase 1 (PRD-1.1) is complete. The Risk Summary Service now provides `get_risk_delta`,
`get_risk_summary`, and `get_risk_change_profile` with explicit typed contracts, canonical
service-error semantics, a shared error envelope, and business-day resolution.

The replay and evidence models (ADR-002, ADR-003) are defined but not yet fully exercised
in the API surface. Phase 2 should build on the established foundations without redesigning them.

Task:

Author the Phase 2 PRD. Identify the next highest-value delivery slice and write a bounded,
implementation-ready PRD that:

1. Names the Phase 2 capability area (e.g. replay verification, API exposure, portfolio
   aggregation, or another logical next step based on the existing ADRs and contracts).
2. Defines the typed contracts, status models, and error semantics for that capability.
3. Identifies which existing shared infrastructure can be reused and which gaps remain.
4. Lists explicit out-of-scope items to prevent scope creep from Phase 1 patterns.
5. Provides issue decomposition guidance — how Phase 2 maps to WI-2.x.y work items.

Required outcomes:

1. Phase 2 capability area identified and justified
2. API surface defined with typed contracts
3. Error and degraded-case semantics explicit
4. Reuse of Phase 1 infrastructure identified
5. Gap analysis (what needs to be built new vs extended)
6. Architecture boundary discipline preserved (modules / walkers / orchestrators / UI)
7. Issue decomposition guidance
8. ADR gaps identified (new decisions that Phase 2 requires)

Important constraints:

- Do not redesign Phase 1 contracts.
- Do not widen existing schemas unless absolutely necessary.
- Do not push ambiguity back to coding.
- Keep the PRD scoped to one coherent capability.
- Preserve consistency with all four accepted ADRs.

Expected result:

A new `docs/prds/phase-2/PRD-2.x-<capability-name>.md` that makes Phase 2 work items
coding-ready without requiring fabricated fields or invented semantics.

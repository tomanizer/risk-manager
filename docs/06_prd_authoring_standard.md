# PRD Authoring Standard

## Purpose

This standard explains how PRDs in this repo should be written so they remain specific to the AI-supported risk manager and do not drift into generic software boilerplate.

PRDs should be implementation-ready, but they should also remain anchored in real risk management work.

## Principle

A good PRD in this repo does not only answer:

- what should be built?

It also answers:

- why does this matter to risk management?
- which process does it support?
- what decision will it influence?
- what evidence, caveats, and degraded states matter?

## Every PRD should include

PRDs must follow the appropriate template in `docs/prd_templates/`. This standard adds risk-mission-specific checks on top of that structure — it does not replace the required template sections (in-scope / out-of-scope, acceptance criteria, test cases, dependencies, and open questions).

### 1. Risk management purpose

State clearly:

- what risk management question the component helps answer
- why that question matters
- what goes wrong operationally if the component is weak or absent

### 2. Supported process context

State which operating model process this PRD supports, for example:

- daily monitoring
- risk investigation
- limit monitoring
- PLA support
- governance pack production
- desk status review
- month-end review

Reference `docs/04_risk_manager_operating_model.md` where appropriate.

### 3. Human user or accountable owner

State:

- who uses the output
- who owns the process
- who decides at the human boundary

### 4. Inputs and outputs in typed form

PRDs should prefer typed contracts and explicit status models.

### 5. Degraded states

PRDs must define:

- what can be missing
- what can be partial
- what can be degraded
- how those states affect interpretation and downstream use

### 6. Evidence expectations

PRDs should say:

- what evidence must be preserved
- what logs or artifacts matter
- what must be replayable

### 7. Decision impact

A PRD should state what decision or downstream action the output supports, for example:

- investigate further
- challenge current explanation
- escalate
- document and close
- approve or reject exception handling

### 8. Explicit non-goals

A PRD should say what the component must not do, especially where autonomy could drift too far.

## What to avoid

Avoid PRDs that are generic in the following ways:

- generic feature-list language without risk context
- vague references to "users" without naming the actual role
- outputs with no statement of operational use
- AI components with no explicit boundary or remit
- missing degraded-state semantics
- no explanation of what evidence matters

## Special guidance for deterministic services

Deterministic-service PRDs should emphasize:

- canonical business rules
- typed schemas
- replay requirements
- status precedence
- fixture-driven tests
- narrow scope

These PRDs should not pretend to be clever. They should be exact.

## Special guidance for walkers

Walker PRDs should emphasize:

- walker mission
- question class answered
- permitted evidence sources
- required caveats
- confidence model
- forbidden actions
- human escalation boundary

These PRDs should not describe walkers as generic assistants.

## Special guidance for orchestrators

Orchestrator PRDs should emphasize:

- triggering conditions
- stage order
- routing logic
- human gates
- evidence handoff
- degraded and retry behavior

## Special guidance for UI and Presentation

UI and Presentation PRDs should emphasize:

- data sources (must consume typed walker or service outputs)
- caveat visibility (must not suppress or hide caveats)
- no logic recomputation (must not re-run business or risk logic)
- user interaction gates (explicitly defining where human decisions occur)
- degraded state rendering (how to show partial or missing data)

## Recommended PRD quality questions

Before accepting a PRD, ask:

- does this sound like a real market risk capability rather than a generic software artifact?
- is the human process context clear?
- is the decision impact clear?
- are degraded states explicit?
- are evidence and replay requirements clear?
- is the autonomy boundary explicit?

## Relationship to other canon documents

PRD authors should use these documents as source context:

- `docs/01_mission_and_design_principles.md`
- `docs/04_risk_manager_operating_model.md`
- `docs/05_walker_charters.md`
- `docs/methodology/01_var_methodology_overview.md`
- `docs/methodology/02_historical_simulation_and_shocks.md`

PRDs should not copy these documents in full. They should reference them and include only the local context needed for implementation.

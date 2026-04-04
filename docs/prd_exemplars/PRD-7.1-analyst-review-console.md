# PRD-7.1: Analyst Review Console

## Variant
UI / Presentation PRD

## Purpose
Provide a controlled analyst-facing workspace for reviewing daily cases, caveats, challenge findings, and evidence links.

## In scope
- case list view
- case detail view
- filters and sorting
- trust state visibility
- challenge visibility
- evidence drill-through
- action summary panel

## Out of scope
- final sign-off execution
- raw data exploration
- workflow logic editing
- custom chart authoring

## Core journeys
1. Review the daily case queue.
2. Open a case and inspect hypotheses, caveats, and actions.
3. Filter blocked or unresolved cases.
4. Drill into evidence links.

## Core UI states
- loading
- ready
- empty
- degraded
- blocked
- error

## Core rules
1. Caveats must be visible near conclusions.
2. Blocked and unresolved states must not be buried.
3. UI consumes typed outputs only.
4. UI must not recompute workflow logic.

## Acceptance criteria
- analyst can review a daily run end to end
- case details are readable and evidence-linked
- degraded and error states display clearly
- branding and severity display rules are respected

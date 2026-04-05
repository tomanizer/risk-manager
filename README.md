# risk-manager

AI-enabled market risk platform for daily investigation, FRTB / PLA controls, limits and approvals, operational integrity, desk status, governance reporting, and controlled change assessment.

## Repository purpose

This repository is the governed source of truth for:
- the target operating model (TOM)
- architecture and design principles
- architectural decision records (ADRs)
- phased implementation roadmap
- PRD templates and exemplars
- work items and prompts for AI-mediated delivery
- source code, tests, and replay fixtures

## Core architecture

The platform is organized into:
1. **Capability Modules**: deterministic logic, business rules, canonical business state, audit trails
2. **Specialist Walkers**: typed interpretation over module outputs
3. **Process Orchestrators**: workflow state, workflow execution, routing, gates, challenge, and handoff

## Design doctrine

- deterministic core, agentic edge
- evidence-first and replayable
- typed interfaces only
- KISS and YAGNI
- no hidden policy in UI
- no raw calculations in orchestrators
- no silent bypass of trust or challenge gates

## Initial canon

See `docs/` for the current approved architecture canon.

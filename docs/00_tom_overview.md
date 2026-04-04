# TOM Overview

## Purpose

This platform is an AI-enabled market risk operating model for:
- daily risk investigation
- FRTB / PLA oversight
- limits and approvals
- controls and production integrity
- desk status and capital consequence views
- governance reporting
- controlled change assessment

## Core architectural principle

The platform separates:
1. **Capability Modules**: own deterministic truth
2. **Specialist Walkers**: interpret truth
3. **Process Orchestrators**: run business workflows

## Capability Modules

- Risk Analytics
- FRTB / PLA Controls
- Limits & Approvals
- Controls & Production Integrity
- Governance & Reporting
- Capital & Desk Status
- Model Inventory / Usage Registry (lightweight at first)

## Specialist Walkers

- Quant Walker
- Time Series Walker
- Data Controller Walker
- Controls / Change Walker
- Market Context Walker
- Governance / Reporting Walker
- Critic / Challenge Walker
- Presentation / Visualization Walker
- Model Risk & Usage Walker

## Process Orchestrators

- Daily Risk Investigation
- Limit Breach
- PLA Deterioration
- Month-End Review
- Desk Status / Capital Impact
- Model / Change Impact
- Governance Pack

## Architectural statement

Deterministic services own calculations, workflow state, policy rules, and audit trails. Walkers interpret through typed interfaces. Orchestrators route, gate, synthesize, challenge, and hand off. No component should silently absorb the responsibilities of another.

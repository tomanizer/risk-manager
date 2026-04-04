# WI-1.1.1

## Linked PRD

PRD-1.1

## Purpose

Define the core enums and typed schemas for the Risk Summary Service.

## Scope

- `MeasureType`
- `SummaryStatus`
- `NodeLevel`
- `NodeRef`
- `RiskSummary`
- `RiskHistoryPoint`
- `RiskHistorySeries`

## Out of scope

- service logic
- fixture loading
- rolling statistics
- history retrieval

## Acceptance Criteria

- schemas are explicit and typed
- nullability is defined
- enums match PRD
- unit tests validate schema behavior

## Suggested Agent

Coding Agent

## Review Focus

- contract fidelity
- schema completeness
- future extensibility without overengineering

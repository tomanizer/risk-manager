# Risk Analytics Capability Overview

## Capability mission

The Risk Analytics module provides canonical quantitative facts for the AI-supported risk manager.

Its job is to answer, in a deterministic and replayable way:

- what is the current risk level?
- what changed?
- where in the hierarchy did it change?
- is the change ordinary or unstable?
- what is known, missing, partial, or degraded about the answer?

It is the factual engine room for later walkers and orchestrators.

## Why it exists

Without a canonical risk analytics layer, every downstream process risks inventing its own version of truth.

That leads to:

- inconsistent numbers across investigations
- repeated business-day logic in many places
- ambiguity about scope
- weak separation between fact and interpretation
- poor replay and auditability

This module exists so that:

- deterministic services own core calculation and retrieval logic
- walkers consume governed facts instead of re-deriving them
- governance outputs trace back to stable, testable contracts

## Supported business questions

The first module slice is designed to support questions such as:

- what is today’s VaR or ES for this node?
- what changed versus the prior business day or an explicit comparison date?
- is the move top-of-house or legal-entity specific?
- is the node simply up or down, or is volatility and instability also rising?
- is the answer complete enough to use safely?

## First slice in scope

The first slice is intentionally narrow.

It covers:

- `RiskSummary`
- `RiskHistorySeries`
- `RiskDelta`
- `RiskChangeProfile`
- scope-aware `NodeRef`
- business-day resolution
- replay by snapshot
- deterministic fixture support

It does not yet cover:

- risk-factor decomposition
- PnL explain
- contributor ranking
- narrative generation
- approvals
- orchestration logic

## Relationship to the hierarchy

The module must support:

- `TOP_OF_HOUSE`
- `LEGAL_ENTITY`

This matters because risk managers need both:

- a whole-firm view
- a legal-entity constrained view of the same logical hierarchy

The same desk or book may exist in both views and may not have the same value in each.

## Relationship to walkers

This module feeds:

- Quant Walker
- Time Series Walker
- Governance and Reporting Walker
- Capital and Desk Status processes
- Daily Risk Investigation orchestrator

It must therefore expose:

- clear status semantics
- deterministic first-order and second-order change metrics
- enough metadata for replay and evidence capture

## Design constraints

### Deterministic only

The module must not contain:

- LLM reasoning
- free-form interpretation
- fuzzy matching
- narrative explanation logic

### Explicit degraded states

The module must surface:

- missing snapshot
- missing node
- missing comparison point
- missing history
- degraded source conditions

### Replayable

The same input plus same snapshot must yield the same output.

### Scope-aware

No result may silently collapse legal-entity-scoped requests into top-of-house behavior.

## Output family summary

### RiskSummary

Use when the caller needs the main current-versus-prior answer with rolling context.

### RiskHistorySeries

Use when the caller needs dated history over a range.

### RiskDelta

Use when the caller needs a minimal first-order movement answer.

### RiskChangeProfile

Use when the caller needs first-order movement plus second-order volatility-aware context.

## Why first-order and second-order change are separated

A simple delta is not enough.

A risk manager cares about both:

- first-order change: what moved
- second-order risk: whether the series has become more unstable, noisy, or regime-shifted

This is why the design keeps `RiskDelta` separate from `RiskChangeProfile`.

## Ownership intent

- business owner: market risk reporting owner
- technical owner: risk analytics owner
- control owner: risk data / controls owner

## Implementation stance

The module should be built in this order:

1. schemas and enums
2. deterministic fixtures
3. business-day resolver
4. history retrieval
5. summary and delta retrieval
6. volatility-aware change profile
7. replay tests
8. usage examples and README documentation

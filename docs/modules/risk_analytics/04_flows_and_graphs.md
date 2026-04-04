# Risk Analytics Flows and Graphs

## Purpose

This document captures the main control flow and data flow for the first module slice.

## Service dependency graph

::: mermaid
flowchart TD
    A[NodeRef and request context] --> B[Business-day resolver]
    A --> C[Current point retrieval]
    B --> D[Comparison date]
    D --> E[Comparison point retrieval]
    A --> F[History retrieval]
    C --> G[RiskDelta]
    E --> G
    C --> H[RiskSummary]
    E --> H
    F --> H
    C --> I[RiskChangeProfile]
    E --> I
    F --> I
:::

## Summary retrieval flow

1. Validate measure and node reference
2. Validate hierarchy scope rules
3. Resolve business-day comparison date if not provided
4. Retrieve current point
5. Retrieve comparison point
6. Retrieve lookback history
7. Compute first-order delta fields
8. Compute rolling statistics
9. Derive status and reasons
10. Return structured output with replay metadata

## Change profile flow

::: mermaid
flowchart LR
    A[Current value] --> D[First-order change]
    B[Comparison value] --> D
    C[History window] --> E[Rolling dispersion]
    D --> F[RiskChangeProfile]
    E --> F
    E --> G[Volatility regime]
    E --> H[Volatility change flag]
    G --> F
    H --> F
:::

## Scope handling graph

::: mermaid
flowchart TD
    A[Incoming NodeRef] --> B{Hierarchy scope}
    B -->|TOP_OF_HOUSE| C[legal_entity_id must be null]
    B -->|LEGAL_ENTITY| D[legal_entity_id required]
    C --> E[Resolve node in full-firm hierarchy]
    D --> F[Resolve node in entity-scoped hierarchy]
    E --> G[Deterministic retrieval]
    F --> G
:::

## Degraded-state decision sketch

::: mermaid
flowchart TD
    A[Request] --> B{Measure supported?}
    B -->|No| U[UNSUPPORTED_MEASURE]
    B -->|Yes| C{Snapshot present?}
    C -->|No| S[MISSING_SNAPSHOT]
    C -->|Yes| D{Node present?}
    D -->|No| N[MISSING_NODE]
    D -->|Yes| E{Snapshot degraded?}
    E -->|Yes| G[DEGRADED]
    E -->|No| H{Compare point missing?}
    H -->|Yes| M[MISSING_COMPARE]
    H -->|No| I{History missing?}
    I -->|Yes| R[MISSING_HISTORY]
    I -->|No| O[OK]
:::

## How this module is used by walkers

### Quant Walker

Consumes:

- `RiskSummary`
- `RiskDelta`
- `RiskChangeProfile`

Needs:

- deterministic change numbers
- hierarchy localization
- explicit degraded states

### Time Series Walker

Consumes:

- `RiskHistorySeries`
- rolling fields from `RiskSummary`
- volatility fields from `RiskChangeProfile`

Needs:

- ordered history
- stable window semantics
- replay consistency

### Governance and Reporting Walker

Consumes:

- structured outputs and statuses
- scope fields
- metadata for evidence capture

Needs:

- explicit caveats
- stable status semantics
- simple exportability

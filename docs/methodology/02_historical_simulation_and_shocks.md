# Historical Simulation And Shocks

## Purpose

This document defines the repository's methodology-facing view of shocks and shock lineage.

It exists because future VaR explain, scenario inspection, and driver analysis depend on consistent shock terminology and deterministic shock contracts.

## Why shocks matter

In historical-simulation-style VaR, the underlying engine is not only the final risk number. It is also the set of historical market moves, factor moves, or transformed scenario states used in the simulation.

If the repository does not define shocks explicitly, later services will drift on:

- what a shock is
- what units it uses
- how it links to factors
- how it links to VaR outputs
- what caveats apply

## Canonical shock concepts

### Shock

A canonical market move or factor change used in VaR or scenario-related computation.

A shock is not the same thing as a final risk result. It is an input or explanatory object in the simulation chain.

### Historical Shock

A shock derived from an observed historical movement over a defined historical interval.

Typical provenance:

- one business-date move
- one historical window observation
- one realized factor or market-state change

### Simulated Shock

A shock produced by a simulated or generated scenario process rather than directly copied from realized historical moves.

### Shock Set

A governed collection of shocks used together for a VaR or scenario run.

A shock set should be versioned and should have explicit methodology meaning.

### Shock Lineage

The deterministic lineage linking:

- source time series or scenario source
- shock transformation
- factor mapping
- simulation run or snapshot
- downstream VaR or explain outputs

## Shock representation

Future shock-facing deterministic services should preserve fields such as:

- `shock_id`
- `shock_set_id`
- `shock_type`
- `source_date` or scenario reference
- `source_interval`
- `factor_ids` or factor-group references
- `transformation_type`
- `magnitude`
- `magnitude_units`
- `currency` if relevant
- `methodology_version`
- `snapshot_id`
- `lineage_refs`
- `caveats`

Exact field names may vary by service, but these concepts should not disappear.

## Common transformation types

Examples include:

- absolute move
- relative return
- log return
- spread move
- curve move
- surface move
- bucketed composite move

Specs should define which transformation type is canonical for a given service.

## Shock caveats

A methodology-aware shock service should preserve caveats such as:

- stale historical source
- missing factor mapping
- incomplete hierarchy coverage
- transformed or compressed shock representation
- methodology-version mismatch

## What should not be left implicit

Future PRDs should not leave these unstated:

- whether shocks are historical or simulated
- whether shock sets are replayable by identifier
- whether lineage is point-to-point or summarized
- whether factor granularity is preserved or aggregated
- whether shock dates are source dates, run dates, or both

## Relationship to the current roadmap

Shock contracts are not required to unblock the current risk-summary history slice.

They are, however, a prerequisite for serious future work in:

- VaR explain
- contributor and driver analysis
- scenario lineage
- methodology-aware challenge and governance output

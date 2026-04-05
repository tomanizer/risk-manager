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

Historical shocks should remain explicit about whether they are:

- raw historical observations
- weighted historical observations
- volatility-filtered or volatility-rescaled observations

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
- `method_variant`
- `magnitude`
- `magnitude_units`
- `currency` if relevant
- `methodology_version`
- `snapshot_id`
- `lookback_window`
- `stress_window_id` when relevant
- `observation_weight` when relevant
- `volatility_filter_id` or equivalent calibration reference when relevant
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

## Historical-simulation variants that affect shock meaning

### Plain historical simulation

Each historical shock is replayed without parametric distribution fitting and with equal weight across the chosen observation window.

### Weighted or hybrid historical simulation

Historical shocks remain empirical observations, but their contribution to tail selection depends on a governed weighting scheme, usually with greater weight on recent observations.

In this case shock lineage should preserve:

- the weighting rule
- the effective lookback period
- the observation weight for a given shock when that weight affects explainability

### Filtered historical simulation

The effective shock is not just the raw historical return. It is the filtered or standardized historical move, rescaled to current volatility conditions.

For filtered methodologies, shock lineage should preserve:

- the original source observation
- the volatility-filter or normalization method
- enough metadata to explain how the historical move was transformed before reuse

## Lookback and stress-window governance

In historical-simulation-style methods, shock sets are governed not only by factor content but also by sampling policy.

Methodology-aware specifications should not leave these choices implicit:

- observation window length
- decay or weighting regime
- whether stressed periods are forced in, separately tagged, or handled through a stressed calibration
- whether the anchor for a request is a valuation date, a snapshot, a source date, or a stress-window identifier

These choices change the meaning of the shock set and therefore must be part of lineage rather than hidden implementation detail.

## Full revaluation and shock application

For nonlinear portfolios, the important object is often not only the shock itself but also the repricing method used when the shock is applied.

Specs should be explicit about whether the historical shock is applied through:

- full revaluation or full repricing
- local sensitivity approximation
- reduced-factor approximation

If a later explain surface will compare shock contributions, the repricing regime must remain governed and visible.

## Shock caveats

A methodology-aware shock service should preserve caveats such as:

- stale historical source
- missing factor mapping
- incomplete hierarchy coverage
- transformed or compressed shock representation
- methodology-version mismatch
- weight or decay choices that materially affect tail selection
- volatility-filter assumptions that may fail in regime change
- approximation error from reduced-factor or local-sensitivity repricing

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

See also:

- `docs/methodology/01_var_methodology_overview.md`
- `docs/methodology/03_advanced_var_methodologies_and_constraints.md`

# VaR Methodology Overview

## Purpose

This document provides a concise methodology reference for VaR-oriented design work in this repository.

It is not intended to replace formal bank methodology documents. It exists to keep repository specs, PRDs, and AI-agent outputs aligned with real market-risk thinking.

## What VaR is

Value at Risk is a loss-threshold measure over a defined horizon and confidence level.

For this repository, VaR-related design should always make these dimensions explicit:

- confidence level
- horizon
- methodology family
- source shock set or scenario set
- aggregation scope
- currency basis
- snapshot and methodology version

## What VaR is not

VaR is not:

- a full explanation of why risk moved
- a substitute for control-quality assessment
- a proof of model sufficiency
- a standalone governance conclusion

It is one governed fact inside a broader risk-management process.

## Main methodology families

### Historical simulation

Uses realized historical market moves or factor moves applied to the current portfolio or risk representation.

### Parametric or variance-covariance approaches

Use distributional assumptions and covariance structure to estimate loss behavior.

### Monte Carlo or scenario simulation

Use simulated or generated market states, often with more complex model structure.

This repository should keep these families conceptually separate even if early implementation focuses on historical-style deterministic outputs first.

## Advanced methodology variants

### Weighted or hybrid historical simulation

Weighted historical simulation, often called hybrid historical simulation, keeps the non-parametric spirit of historical simulation but applies greater weight to more recent observations.

This improves responsiveness to volatility shifts, but it introduces a governed design choice:

- decay scheme
- effective lookback length
- treatment of older stress observations

### Filtered historical simulation

Filtered historical simulation adjusts historical returns for changing volatility before they are reused in the VaR engine.

In practice this usually means:

- estimate conditional volatility with a model such as EWMA or GARCH-family volatility
- standardize or filter historical returns
- rescale them to current volatility conditions

This can make risk estimates more reactive to regime change, but it also introduces model-risk questions around the volatility filter itself.

### Full revaluation or full repricing

Full revaluation recalculates the portfolio under each simulated or historical scenario using pricing logic rather than relying only on local sensitivities such as delta or delta-gamma approximations.

This matters most for:

- options and embedded optionality
- callable or prepayable fixed-income instruments
- portfolios with strong curvature or discontinuous payoffs

The benefit is accuracy for nonlinear portfolios. The tradeoff is computational cost, pricing-model dependency, and operational complexity.

### Principal-component or reduced-factor approximations

Reduced-factor methods compress the risk-factor space to improve runtime.

They can be useful, but they should be treated as approximations whose fidelity depends on:

- how much variance the reduced factor set retains
- whether omitted dimensions matter in the tails
- whether the portfolio payoff is highly nonlinear in the omitted dimensions

### Long-memory volatility extensions

Long-memory volatility models such as FIGARCH-style approaches appear in the literature as a way to capture persistent volatility behavior that decays more slowly than in standard short-memory GARCH-style models.

These methods can improve VaR forecasts in some datasets, but they should be treated in this repository as specialist or research-oriented extensions, not as the default enterprise baseline.

## Why methodology matters for this repository

An AI-supported risk manager needs more than a summary number.

To support investigation, challenge, and governance, methodology-aware designs should preserve:

- where the number came from
- which shock or scenario set drove it
- which data and mapping assumptions apply
- which caveats limit interpretation

## Core methodological distinctions

### Summary versus driver

A VaR summary tells you the level or change.

A methodology-aware driver layer tells you:

- which shocks or scenarios matter
- which factors moved
- whether the result reflects market behavior, model structure, data defects, or a mixture

### First-order versus second-order interpretation

First-order change is a direct movement in the reported measure.

Second-order interpretation concerns:

- dispersion
- instability
- concentration
- regime sensitivity

### Market move versus operational artifact

VaR movement can reflect:

- genuine market conditions
- position changes
- mapping errors
- stale inputs
- methodology changes
- control defects

Specs should preserve these distinctions explicitly.

### Internal risk management versus regulatory capital

Internal VaR usage and regulatory capital methodology are related but not identical.

The repository should make the intended context explicit:

- internal daily or intraday risk management
- risk-manager investigation support
- model validation or backtesting support
- regulatory capital support

This matters because the regulatory market-risk framework has moved beyond plain VaR for capital purposes.

## Methodology caveats that should surface in specs

- lookback coverage may be sparse or unrepresentative
- business-day calendars matter
- shock lineage may be incomplete
- factor mappings may drift over time
- snapshot quality may degrade interpretation
- comparison across scopes may not be symmetric
- volatility filters may be mis-specified
- nonlinear repricing shortcuts may miss tail behavior
- stress windows and recent weighting may pull in different directions
- liquidity or funding stress may sit outside plain VaR unless modelled explicitly

## Lookback windows, stress windows, and anchoring

The loose phrase "time-series anchor" is too imprecise for methodology work.

Specs should instead say which of these are in play:

- lookback window
- decay or weighting scheme
- stress window or stressed calibration period
- anchor snapshot or anchor valuation date

These are different concepts and should not be collapsed into one vague term.

## Regulatory context that should not be ignored

VaR remains useful for internal market-risk measurement, desk-level monitoring, scenario comparison, and explain workflows.

However, a methodology-aware repository should remember:

- Basel 2.5 supplemented VaR with stressed VaR
- the FRTB internal-models framework replaced VaR and stressed VaR with expected shortfall for capital measurement
- FRTB also introduced liquidity horizons, non-modellable risk-factor treatment, and stronger P&L attribution (RTPL vs HPL) and backtesting gates

This means a specification should say whether it is building:

- an internal VaR-oriented deterministic service
- a regulatory-capital support service
- or a shared capability that must keep both contexts distinct

## Boundary concepts that should not be conflated

### Funding and liquidity stress

Funding stress and market illiquidity are real risk-management concerns, but plain VaR does not capture them automatically.

If the use case depends on funding or liquidity behavior, the specification should say so explicitly rather than implying that a standard VaR engine is sufficient.

### Credit cohort analysis

Credit-cohort analysis is a valid risk methodology in credit-risk and portfolio-performance contexts, but it is not a standard core concept inside trading-book market VaR methodology.

Do not inject cohort terminology into market-VaR specifications unless the capability genuinely crosses into credit-portfolio analytics.

## What should be versioned

Methodology-aware services should make versioning explicit for:

- data snapshot
- methodology version
- configuration or threshold version
- shock-set or scenario-set version where relevant

## Implementation implications

Methodology-facing PRDs should say:

- which methodology family is assumed
- which advanced variant is assumed, if any
- whether the portfolio is treated with full revaluation or local approximation
- whether the context is internal risk, validation, or regulatory support
- whether shocks are historical, simulated, or both
- which objects represent canonical methodological truth
- which caveats must be preserved downstream
- what the system must not infer automatically

Methodology-facing PRDs should also be explicit about:

- lookback window and stressed-window choices
- decay or weighting scheme
- volatility filter or normalization method if used
- how backtesting or violation clustering should be interpreted
- whether liquidity-horizon or expected-shortfall concepts are in or out of scope

## Relationship to future work

This overview is a foundation for later deterministic services such as:

- shock catalog and lineage
- historical VaR explain support
- scenario-set inspection
- concentration and tail-driver services

See also:

- `docs/methodology/02_historical_simulation_and_shocks.md`
- `docs/methodology/03_advanced_var_methodologies_and_constraints.md`

# Advanced VaR Methodologies And Constraints

## Purpose

This document deepens the repository's VaR methodology canon beyond the three broad method families.

It exists to keep future specifications precise about:

- weighting and filtering choices
- nonlinear repricing choices
- tail-risk and liquidity limitations
- the boundary between internal VaR usage and regulatory capital methodology

## Method selection starts with the use case

Before specifying a VaR-oriented capability, make these questions explicit:

- Is the output for internal desk monitoring, investigation support, model validation, or regulatory support?
- Is the portfolio materially nonlinear?
- Is regime adaptiveness more important than long stress coverage, or vice versa?
- Does the use case require fully replayable shock lineage?
- Is runtime a hard constraint?

There is no single "best VaR methodology" without these answers.

## Weighted and hybrid historical simulation

Weighted historical simulation, often called hybrid historical simulation, combines historical simulation with an exponentially decaying weighting scheme.

Why teams use it:

- retain empirical tail shape from historical data
- react faster to recent volatility conditions than flat-weight historical simulation
- avoid a full normality assumption

What must be explicit in specs:

- decay parameter or weighting regime
- observation window
- treatment of older stress periods
- whether weighting affects downstream shock explain

## Filtered historical simulation

Filtered historical simulation modifies historical simulation by filtering or standardizing historical returns with a volatility model and then rescaling them to current volatility conditions.

Why teams use it:

- make VaR more responsive to changing regimes
- avoid treating old high-volatility observations and current low-volatility states as directly comparable without adjustment

What must be explicit in specs:

- volatility model family, such as EWMA or a GARCH-style model
- whether filtering is done at factor level or portfolio level
- what calibration window governs the filter
- how transformed shocks remain replayable and explainable

## Full revaluation versus local approximations and grid methods

For portfolios with meaningful nonlinearity, the distinction between full revaluation and approximation-based repricing is fundamental.

### Full revaluation

Reprice each position or the full portfolio under each scenario using the relevant pricing logic.

Benefits:

- higher fidelity for options, callable structures, and curvature-heavy books
- better alignment with front-office pricing logic when implemented well

Costs:

- materially higher runtime
- stronger dependency on pricing-model governance
- harder operational support

### Local sensitivity approximations

Use delta, delta-gamma, or similar local approximations instead of full repricing.

Benefits:

- speed
- operational simplicity

Risks:

- tail behavior may be mismeasured
- discontinuous or strongly nonlinear payoffs may be missed
- explain surfaces may overstate precision if the approximation is hidden

### Grid methods or grid calculation

Some institutions also use grid terminology, such as:

- grid calculation
- grid methodology
- grid valuation
- grid-based approximation

This usually refers to precomputed valuation surfaces, factor-sensitivity grids, or stored grids of portfolio values that are later interpolated during VaR calculation.

Important boundary:

- a grid method belongs to the approximation family
- but it is not identical to a plain local Taylor approximation such as delta or delta-gamma

In other words, both local sensitivity methods and grid methods are alternatives to full revaluation, but they are not interchangeable labels in a strict technical sense.

What must be explicit in specs:

- whether "grid" means a stored sensitivity grid, a stored portfolio-value grid, or another interpolation surface
- whether the grid is being used instead of full repricing
- what approximation error is accepted
- whether the use case still requires explainability of repricing lineage

## Monte Carlo and scenario-simulation approaches

Monte Carlo VaR generates hypothetical scenarios from an explicit stochastic model and revalues the portfolio under those scenarios.

This is often appropriate when:

- the factor distribution is not well represented by a finite historical window
- the use case needs more flexible scenario generation
- the portfolio is materially nonlinear and already depends on repricing machinery

Scenario simulation and reduced-factor methods can improve runtime, but they introduce additional approximation choices that must stay visible in canon.

## Long-memory volatility approaches

Long-memory volatility approaches, such as FIGARCH-style extensions, attempt to capture very persistent volatility behavior that standard short-memory filters may understate.

Important caveat:

- some literature finds improved VaR or ES forecasting from long-memory volatility models in specific datasets
- other literature finds that apparent long memory can be overstated when structural breaks or time-varying unconditional variance are ignored

Repository stance:

- treat these as specialist or research-oriented extensions
- do not assume they are the default production baseline
- require explicit evidence before building them into canonical services

These methods belong in scope only when the specification can justify why persistence structure matters materially for the target use case.

## Stress windows, anchors, and calibration choices

Advanced VaR methodology is often less about inventing a new engine than about governing calibration choices correctly.

These choices should be explicit:

- long-window historical sampling versus short-window responsiveness
- explicit stressed calibration period versus recency weighting
- anchor snapshot versus source-date semantics
- business-day and holiday treatment

In this repository, "anchor" should never be left as a vague term. The spec should name whether the anchor is:

- valuation date
- snapshot id
- source-date window
- stressed calibration window

## Backtesting and clustering of violations

A methodology-aware specification should not reduce model validation to simple exception counting.

Key points:

- unconditional breach counts matter
- clustering of violations matters
- a model can appear acceptable on raw exception rate and still adapt poorly to regime change
- regulatory internal-model contexts also care about P&L attribution, not just raw backtesting counts

If a service will be used in validation or governance workflows, these distinctions should be preserved explicitly.

## Regulatory context: VaR, stressed VaR, and expected shortfall

For regulatory market risk, the context matters:

- Basel 2.5 added stressed VaR to address weaknesses in plain VaR
- the FRTB internal-models framework replaced VaR and stressed VaR with expected shortfall for capital measurement
- FRTB also introduced liquidity horizons, non-modellable risk-factor treatment, and stronger desk-level model approval controls

Repository stance:

- internal VaR services are still valid and useful
- regulatory-capital support should not pretend that plain VaR is the current full answer for capital methodology
- specifications must say when they cross from internal VaR analytics into regulatory-capital support

## Liquidity and funding constraints

Plain VaR is not a complete model of liquidity stress or funding stress.

If the use case depends materially on:

- liquidation horizons
- market depth
- funding squeezes
- basis blowouts driven by stress liquidity

then the spec should say so explicitly rather than implying that a standard VaR engine captures it.

## What does not belong in market-VaR canon by default

### Credit cohorts

Credit-cohort analysis is an important technique in credit-risk and loan-performance contexts, but it is not a standard core object in trading-book market VaR methodology.

Do not import cohort terminology into market-VaR specs unless the capability explicitly spans credit-portfolio analytics.

### Generic "advanced risk management" claims

Do not label a methodology as advanced merely because it is computationally heavier.

The relevant question is whether the method is better aligned to:

- the portfolio's payoff structure
- the required tail fidelity
- the regime behavior of the market data
- the regulatory or governance context

## Industry aliases and naming conventions

Methodology specs should add aliases when industry usage is known to vary across desks, vendors, or regulators.

The purpose is not to multiply jargon. The purpose is to stop agents from mistaking two labels for two different concepts, or collapsing two genuinely different concepts into one label.

Useful examples:

- weighted historical simulation = hybrid historical simulation
- full revaluation = full repricing
- local sensitivity approximation may be called approximation VaR, delta-based VaR, or local approximation
- grid calculation or grid methodology usually refers to a grid-based approximation method, not to full revaluation
- expected shortfall may also appear as ES, and older material may still use CVaR or expected tail loss in adjacent contexts
- stressed calibration period may also be called a stress window or stressed window

Rule:

- when two labels are true aliases, say so explicitly
- when one label is only a nearby industry shorthand, say that too
- do not present grid methods as exact synonyms for plain local Taylor approximations
- do not present older regulatory labels as if they were current endpoint methodology without context

## What the spec agent should force into the open

For advanced VaR work, the spec agent should make these choices explicit:

- method family and method variant
- scenario source and calibration window
- weighting or filtering scheme
- repricing fidelity
- replay and lineage expectations
- internal versus regulatory context
- limitations that remain even after the "advanced" method is chosen

## Selected references

- Boudoukh, Richardson, and Whitelaw, *The Best of Both Worlds: A Hybrid Approach to Calculating Value at Risk* (weighted historical simulation / hybrid VaR)
- Barone-Adesi, Giannopoulos, and Vosper, filtered historical simulation papers and follow-on documentation
- MSCI, *Risk Management, a Practical Guide* (overview of parametric, historical simulation, Monte Carlo, and nonlinear repricing implications)
- Office of the Comptroller of the Currency, *An Empirical Evaluation of Value at Risk by Scenario Simulation* (full revaluation, Taylor approximation limits, and reduced-factor scenario methods)
- Basel Committee on Banking Supervision, *Explanatory note on the minimum capital requirements for market risk* (stressed VaR history, expected shortfall, liquidity horizons, and FRTB controls)

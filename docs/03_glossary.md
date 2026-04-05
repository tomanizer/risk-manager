# Glossary

## Core terms

### Capability Module
Deterministic component that owns canonical logic, state, rules, and audit trails.

### Specialist Walker
Agentic specialist that interprets typed outputs from modules.

### Process Orchestrator
Workflow controller that routes work across modules and walkers.

### Target
A specific scope and issue selected for investigation.

### Scope
The object under review, such as desk, book, position, trade, or issue family.

### Trust State
Machine-readable assessment of whether output is safe to interpret.

### Caveat
Explicit limitation that must accompany a finding or report.

### False Signal
Apparent issue likely driven by operational contamination rather than real business or market behavior.

### Handoff Package
Structured output passed from an orchestrator to reporting or downstream workflows.

### Watchlist
Managed state indicating that a desk or issue requires elevated monitoring.

### Replay
Ability to reproduce outputs using the same inputs, snapshots, versions, and rules.

### Risk Factor
A canonical market-risk input dimension such as rate, spread, credit, FX, equity, or volatility component used in risk methodology and simulation.

### Shock
A canonical market move or factor change used in VaR or scenario-related computation.

### Historical Shock
A shock derived from an observed historical market or factor movement over a defined interval.

### Simulated Shock
A shock produced by a simulated scenario process rather than copied directly from realized history.

### Shock Set
A governed collection of shocks used together for a VaR or scenario run.

### Shock Lineage
The deterministic provenance linking source data, transformation, factor mapping, shock set, and downstream risk outputs.

### Weighted Historical Simulation
A historical-simulation VaR variant that applies greater weight to more recent observations rather than using equal weight across the lookback window.

### Filtered Historical Simulation
A historical-simulation VaR variant that adjusts historical returns for changing volatility before using them in the loss distribution.

### Full Revaluation
Repricing positions under each scenario using pricing logic rather than relying only on local sensitivities.

### Grid Methodology
An approximation-based VaR repricing approach that uses precomputed valuation grids, factor-sensitivity grids, or stored portfolio-value grids and interpolates on those grids during calculation. In industry usage it may also be called grid calculation or grid valuation.

### Stressed VaR
A VaR measure calibrated to stressed market conditions, introduced in Basel 2.5 as a supplement to plain VaR for market-risk capital.

### Expected Shortfall
The average loss beyond a chosen tail threshold, used in the FRTB internal-models framework instead of VaR for market-risk capital measurement.

### Liquidity Horizon
The time assumed to exit or hedge a risk factor under stressed market conditions without materially affecting market prices.

### Stress Window
A governed historical period or calibration window chosen to represent stressed market conditions for risk measurement or capital purposes.

### P&L Attribution
A regulatory validation test comparing modelled and observed desk P&L drivers to assess whether an internal market-risk model captures the risks that matter in practice.

### Non-Modellable Risk Factor
A risk factor that lacks sufficient real-price observations for internal-model treatment under the FRTB framework and therefore requires separate capital treatment.

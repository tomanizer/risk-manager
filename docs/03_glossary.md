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

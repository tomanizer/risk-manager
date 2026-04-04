# Walker Charters

## Purpose

This document defines the roles, remits, boundaries, and expected outputs of the specialist walkers.

Walkers are not generic agents. Each walker exists to answer a bounded class of risk management questions using explicit evidence and defined tool permissions.

## Common expectations for all walkers

Every walker must:

- stay inside its remit
- prefer deterministic services and evidence over speculation
- state caveats explicitly
- distinguish confirmed fact from interpretation
- expose confidence and uncertainty clearly
- support replay and documentation where possible
- avoid making human governance decisions

Every walker must not:

- invent unsupported facts
- silently override deterministic results
- absorb sign-off authority
- hide degraded data conditions
- claim certainty when evidence is incomplete

## Standard walker output shape

Each walker should produce a typed or structured result with at least:

- target or scope investigated
- question answered
- key findings
- evidence references
- caveats
- confidence level
- recommended next step
- escalation suggestion if relevant

## Quant Walker

### Mission

Explain quantitative changes in risk using governed risk measures and hierarchy-aware comparisons.

### Core questions

- what changed quantitatively?
- how large is the movement?
- where in the hierarchy is the move concentrated?
- is the change first-order movement, second-order instability, or both?

### Typical inputs

- VaR summaries
- ES summaries
- risk deltas
- risk change profiles
- hierarchy views
- concentration metrics

### Typical outputs

- quantitative change summary
- hierarchy localization
- significance assessment
- first-order versus second-order distinction
- candidate areas for deeper investigation

### Confidence model

Higher confidence when deterministic risk summaries, history, and scope are complete.

Lower confidence when snapshots are partial, hierarchy coverage is incomplete, or volatility context is weak.

### Must not do

- diagnose data defects without Data Controller support
- declare final governance closure
- invent economic narratives without support from other walkers

## Time Series Walker

### Mission

Assess whether observed movement is stable, unusual, trending, regime-shifting, or volatility-driven over time.

### Core questions

- is this move unusual relative to history?
- is volatility rising or falling?
- is the series noisy, stable, or regime-changing?
- does the current point look like an outlier?

### Typical inputs

- risk history series
- rolling statistics
- volatility flags
- comparison windows
- historical control markers

### Typical outputs

- trend assessment
- outlier or regime-change signals
- volatility interpretation
- comparison-window caveats

### Confidence model

Higher confidence when history is sufficiently deep and stable.

Lower confidence when history is sparse, scope has changed, or source data is degraded.

### Must not do

- determine whether a move is economically sensible on its own
- override snapshot quality warnings

## Data Controller Walker

### Mission

Assess whether the data is trustworthy enough for downstream interpretation.

### Core questions

- can this data be used safely?
- what is missing, stale, partial, or inconsistent?
- are there defects that could explain the apparent risk movement?

### Typical inputs

- snapshot metadata
- completeness indicators
- lineage markers
- data quality signals
- control defect feeds

### Typical outputs

- trust state
- defect summary
- caveats for downstream walkers
- block or caution recommendation

### Confidence model

Driven by objective control and completeness evidence rather than subjective interpretation.

### Must not do

- provide market explanations
- resolve governance decisions

## Controls and Change Walker

### Mission

Assess whether technical, model, process, booking, or control changes may explain part of an observed movement.

### Core questions

- did something operational change?
- was there a model, configuration, mapping, or process alteration?
- could a control issue explain all or part of the move?

### Typical inputs

- change logs
- release markers
- mapping/configuration changes
- control incident signals
- model deployment metadata

### Typical outputs

- change-impact summary
- possible operational explanations
- caveats against pure market attribution
- escalation suggestions for control ownership

### Must not do

- claim a move is fully market-driven without considering control context
- sign off remediation

## Market Context Walker

### Mission

Connect observed risk movement to external market context and plausible business drivers.

### Core questions

- what happened in markets that may explain this move?
- are there rate, spread, credit, vol, macro, or event-driven explanations?
- how plausible is the market narrative relative to the timing and hierarchy location?

### Typical inputs

- market data summaries
- event context
- instrument or desk context
- outputs from Quant and Time Series walkers

### Typical outputs

- plausible market narratives
- alignment or mismatch with observed risk movement
- external context notes
- caveats where the fit is weak

### Must not do

- override control or data warnings
- present news-like color as if it were proof

## Governance and Reporting Walker

### Mission

Transform investigation output into governance-ready summaries, packs, and escalation material.

### Core questions

- what does management need to know?
- what should be included in a governance pack?
- what is the documented conclusion, caveat, and next action?

### Typical inputs

- findings from all other walkers
- status flags
- ownership data
- escalation thresholds

### Typical outputs

- management summary
- governance-ready explanation
- evidence checklist
- open actions and owners

### Must not do

- fabricate confidence not present in source walkers
- sign off on behalf of accountable humans

## Critic or Challenge Walker

### Mission

Interrogate the current explanation and identify weak assumptions, missing evidence, and alternative interpretations.

### Core questions

- what is weak or unsupported in the current story?
- what alternative explanation remains plausible?
- where should a human risk manager challenge more deeply?

### Typical inputs

- all current findings
- evidence references
- caveat lists
- missing-data markers

### Typical outputs

- challenge points
- alternative hypotheses
- missing evidence requests
- confidence downgrades where warranted

### Must not do

- block progress without stating clear reasons
- become a generic contrarian with no evidence basis

## Presentation and Visualization Walker

### Mission

Present risk findings in the clearest human-readable format using sound communication and design principles.

### Core questions

- what is the clearest way to show this to the user?
- what view, chart, summary, or layout best supports understanding and decision-making?
- how should caveats be surfaced without hiding the main message?

### Typical inputs

- structured findings
- quantitative summaries
- governance outputs
- branding and presentation rules

### Typical outputs

- human-readable summaries
- presentation structures
- chart recommendations
- concise management views

### Must not do

- distort uncertainty for visual neatness
- invent analysis beyond supplied findings

## Model Risk and Usage Walker

### Mission

Assess whether model limitations, usage boundaries, assumptions, or open issues are relevant to the observed situation.

### Core questions

- is the model being used within intended scope?
- do known limitations affect interpretation?
- are there model issues or assumptions that should caveat the conclusion?

### Typical inputs

- model inventory
- model usage metadata
- known limitations
- open issues and remediation items
- methodology markers

### Typical outputs

- model-risk caveats
- usage-boundary assessment
- relevance of known limitations
- recommendation for model-risk escalation if needed

### Must not do

- replace formal model validation
- invent limitations not present in governed model records

## Relationship between walkers

Walkers are complementary, not hierarchical.

A typical investigation may look like this:

1. Data Controller establishes whether the evidence base is usable
2. Quant Walker explains what changed
3. Time Series Walker adds historical and volatility context
4. Controls and Change Walker checks for operational causes
5. Market Context Walker checks for economic plausibility
6. Model Risk and Usage Walker adds model caveats where relevant
7. Critic or Challenge Walker interrogates the emerging conclusion
8. Governance and Reporting Walker prepares decision-ready output
9. Presentation and Visualization Walker tailors the output for human consumption

## Human boundary

No walker may silently become the decision-maker.

Walkers support:

- investigation
- interpretation
- challenge
- presentation
- evidence packaging

Humans own:

- approvals
- sign-off
- formal challenge outcomes
- escalation decisions
- policy interpretation

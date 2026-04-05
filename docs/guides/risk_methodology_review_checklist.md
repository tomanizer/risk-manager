# Risk Methodology Review Checklist

## Purpose

Use this checklist when reviewing methodology-facing PRDs, design notes, and implementation plans for market-risk capabilities.

## Core questions

### 1. Is the risk concept defined precisely?

- Is the document clear about the underlying concept?
- Are key terms such as VaR, shock, scenario, factor, lineage, expected shortfall, liquidity horizon, or full revaluation used consistently?
- Where industry aliases exist, does the document say which labels are true synonyms and which are only related approximations?

### 2. Does the document sound like market-risk work rather than generic software work?

- Is the operating context clear?
- Does the output support a real risk-manager decision or investigation step?

### 3. Are methodology caveats explicit?

- Are limitations, caveats, and false-signal pathways identified?
- Does the document separate market behavior from data or control artifacts?
- Does it say what plain VaR will still fail to capture, such as illiquidity or funding stress, when that matters?

### 4. Are deterministic and interpretive responsibilities separated?

- Are methodology facts owned by deterministic services?
- Are walkers or narratives prevented from inventing canonical methodological truth?

### 5. Are shock and scenario concepts handled correctly where relevant?

- Is the repository explicit about whether shocks are historical or simulated?
- Is lineage or provenance preserved where the use case depends on it?
- If historical simulation is used, are weighting, filtering, or stress-window choices explicit?

### 6. Are model-choice assumptions explicit?

- Does the document say whether the method is plain HS, weighted HS, filtered HS, parametric, Monte Carlo, or another governed variant?
- Does it say whether nonlinear portfolios require full revaluation or whether an approximation is explicitly accepted?
- Is the difference between internal analytics and regulatory-capital context explicit?

### 7. Are human decision boundaries explicit?

- What does the output help a risk manager decide?
- What remains a human judgment or governance act?

## Failure patterns to flag

- generic finance language with no methodology precision
- missing shock or scenario definitions where they are clearly relevant
- unexplained assumptions about factor lineage
- vague claims about "advanced VaR" with no explicit model variant
- hidden repricing approximations for nonlinear books
- cross-domain drift, such as treating credit-cohort analytics as if it were a core market-VaR concept
- missing caveats around sparse or degraded data
- outputs that look polished but are not methodologically grounded

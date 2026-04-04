# Risk Manager Operating Model

## Purpose

This document explains what a market risk manager actually does, which recurring processes the AI-supported risk manager is meant to support, and why those processes matter.

It exists so that implementation work stays anchored in real operating practice rather than drifting into generic software design.

## The role of a market risk manager

A market risk manager does not merely read reports. The role combines monitoring, investigation, challenge, escalation, documentation, and governance.

A risk manager must repeatedly answer questions such as:

- what changed in the firm’s risk profile?
- is the change expected or surprising?
- what is driving it?
- is the explanation economic, technical, operational, or mixed?
- is the desk still operating within limits, policy, and acceptable control quality?
- does this require escalation, approval, or remediation?

## Core outcomes a risk manager must produce

A good risk management process produces:

- situational awareness
- clear explanation of material movements
- distinction between market events and operational defects
- challenge where the first explanation is weak or incomplete
- explicit caveats and uncertainty
- documented evidence for governance and audit
- escalation when thresholds, policy, or confidence conditions require it

## Main process families

### 1. Daily risk monitoring

The daily cycle asks:

- what moved in VaR, ES, desk risk, or capital status?
- what breached thresholds or changed materially?
- where do we need deeper investigation?

Typical activities:

- review current versus prior values
- compare top-of-house and legal-entity views
- identify large movers
- flag unusual concentrations or volatility shifts
- review data and control quality context

### 2. Investigation of risk changes

Once a move is flagged, the risk manager investigates.

Typical questions:

- did positions change?
- did market levels or volatilities change?
- did correlations or concentration profiles shift?
- did model inputs or methodology change?
- did data degrade?
- is there a known business event or market event behind it?

The goal is not merely to produce any explanation. The goal is to produce the best supported explanation available and to state clearly where confidence is limited.

### 3. Limit monitoring and breach handling

A risk manager monitors:

- hard limit breaches
- soft threshold breaches
- concentration issues
- repeated near-breach patterns
- temporary approvals and expiry conditions

Required outcomes include:

- breach classification
- ownership identification
- evidence package
- escalation route
- approval or remediation path
- closure documentation

### 4. FRTB and PLA-related control support

Where relevant, the operating model also supports investigation around:

- HPL
- RTPL
- PnL vectors
- PLA deterioration
- correlation behavior
- Kolmogorov-Smirnov style distribution tests
- desk status and capital implications

These are not merely statistical artifacts. They affect whether a desk remains in an acceptable regime and whether capital treatment or governance response changes.

### 5. Desk status and capital review

A risk manager needs to understand whether a desk’s condition is improving, stable, or deteriorating.

This can include:

- persistent PLA weakness
- recurring control defects
- unusual capital consumption patterns
- concentration growth
- unstable model usage or scope drift
- recurring unexplained movements

### 6. Governance and reporting

Risk management work must be documented for:

- daily management visibility
- desk discussions
- control forums
- governance committees
- sign-off packs
- audit and replay

This means outputs need to be understandable, evidence-backed, and appropriately caveated.

### 7. Month-end and recurring control cycles

Some processes are cyclical rather than purely event-driven.

Examples:

- month-end review
- recurring approval review
- control attestation support
- periodic model usage review
- recurring desk health assessment

## Why investigation happens

Investigation is usually triggered by one or more of the following:

- large day-on-day move
- threshold or limit breach
- unusual volatility profile
- deterioration in PLA or related metrics
- desk status concerns
- data quality defects
- control alerts
- model or configuration change
- significant market event
- management or governance request

## How a risk manager thinks during investigation

A disciplined investigation usually follows this shape:

1. Confirm the move is real
2. Confirm the data is trustworthy enough
3. Localize where the move sits in the hierarchy
4. Compare current state to prior state and recent history
5. Consider plausible business and market explanations
6. Check whether control, data, booking, or model changes could explain part of the move
7. Challenge the first explanation if confidence is weak
8. Decide whether to close, escalate, or continue
9. Document evidence, caveats, and ownership

## Human decision gates

The AI-supported system may assist analysis, but certain actions remain explicit human decisions.

Examples:

- final sign-off
- approval of breach exceptions
- formal governance conclusions
- material challenge to desk-provided explanations
- closure of significant incidents
- policy interpretation

## What the AI-supported system should improve

The system should improve the operating model by making it easier to:

- find the right evidence quickly
- see both top-of-house and legal-entity views
- distinguish market signal from operational noise
- generate consistent first-pass investigations
- identify where confidence is weak
- support structured challenge
- preserve replayable evidence for governance

## What the system must not collapse together

The operating model depends on keeping these distinctions clear:

- deterministic fact versus inferred explanation
- first-order movement versus second-order instability
- market move versus data issue
- model effect versus business effect
- suggestion versus decision
- support versus sign-off

## Relationship to architecture

The architecture exists to support this operating model.

- deterministic modules provide trusted facts
- walkers perform bounded investigation
- orchestrators run recurring processes and event-driven flows
- human users make accountable decisions

## Implication for future PRDs

Every meaningful PRD should state:

- which process family it supports
- which risk manager questions it helps answer
- which decisions it influences
- what errors or degraded states matter operationally
- what evidence must be preserved

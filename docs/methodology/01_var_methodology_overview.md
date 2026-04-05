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

## Methodology caveats that should surface in specs

- lookback coverage may be sparse or unrepresentative
- business-day calendars matter
- shock lineage may be incomplete
- factor mappings may drift over time
- snapshot quality may degrade interpretation
- comparison across scopes may not be symmetric

## What should be versioned

Methodology-aware services should make versioning explicit for:

- data snapshot
- methodology version
- configuration or threshold version
- shock-set or scenario-set version where relevant

## Implementation implications

Methodology-facing PRDs should say:

- which methodology family is assumed
- whether shocks are historical, simulated, or both
- which objects represent canonical methodological truth
- which caveats must be preserved downstream
- what the system must not infer automatically

## Relationship to future work

This overview is a foundation for later deterministic services such as:

- shock catalog and lineage
- historical VaR explain support
- scenario-set inspection
- concentration and tail-driver services

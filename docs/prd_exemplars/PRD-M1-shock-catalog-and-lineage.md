# PRD-M1: Shock Catalog And Lineage Service

## Variant

Deterministic Service PRD

## Purpose

Provide the canonical deterministic service for retrieving governed shock definitions, shock-set metadata, and shock lineage needed for historical-simulation-style VaR explain and related investigation flows.

## Risk management purpose

This service helps answer:

- which shocks are in scope for this run?
- what type of shocks are they?
- what source dates or scenario sources produced them?
- how do those shocks link to downstream VaR or explain outputs?

## In scope

- shock metadata retrieval
- shock-set metadata retrieval
- historical versus simulated shock classification
- source-date and snapshot lineage
- factor or factor-group linkage
- deterministic caveat flags

## Out of scope

- running VaR itself
- ranking contributors
- narrative generation
- governance sign-off
- stochastic simulation logic

## Core output

`ShockRecord`

- `shock_id`
- `shock_set_id`
- `shock_type`
- `source_date`
- `factor_refs`
- `transformation_type`
- `magnitude`
- `magnitude_units`
- `methodology_version`
- `snapshot_id`
- `lineage_refs`
- `caveats`

## Core rules

1. Every shock must have explicit provenance.
2. Historical and simulated shocks must not be conflated.
3. Shock-set identity must be explicit and versioned.
4. The service is deterministic and replayable.

## Acceptance criteria

- retrieves deterministic shock metadata by id or shock-set id
- preserves source lineage fields explicitly
- distinguishes historical and simulated shocks correctly
- exposes caveats without narrative invention

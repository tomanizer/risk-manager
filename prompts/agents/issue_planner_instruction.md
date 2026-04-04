# Issue Planner Instruction

## Mission

Decompose PRDs and design artifacts into implementation-ready work items that are narrow, testable, and sequence-aware.

## Primary objectives

- split large requirements into coherent slices
- keep issues small enough for coding agents to complete reliably
- preserve dependency logic
- make acceptance criteria explicit

## Good issue qualities

A good issue should be:

- narrow
- testable
- linked to one main outcome
- explicit about what is in scope and out of scope
- linked to the canonical PRD and module docs

## Decomposition rules

### Prefer vertical slices when sensible

Where possible, define issues that produce a usable increment rather than isolated fragments.

### Preserve contract-first sequencing

When contracts are still fluid, create schema and fixture issues before service logic issues.

### Separate deterministic core from interpretation layers

Do not mix deterministic service implementation with walker or presentation logic in one issue.

### Include dependencies explicitly

Every issue should say whether it depends on earlier work.

## Expected issue fields

- linked PRD
- purpose
- scope
- out of scope
- dependencies
- acceptance criteria
- suggested agent
- review focus

## What to avoid

- omnibus implementation tickets
- vague goals like "build service"
- missing acceptance criteria
- hidden dependencies
- mixing code, design, and governance changes without explanation

# Coding Agent Instruction

## Mission

Implement work items faithfully, narrowly, and deterministically.

The coding agent is not a product strategist. It is an implementation agent working from canon documents, PRDs, and work items.

## Primary objectives

- implement only the scoped work item
- preserve contract fidelity
- keep code simple and modular
- add tests with the change
- preserve replayability and explicit degraded states

## Required sources of truth

Before coding, consult in this order:

1. linked work item
2. linked PRD
3. module documentation pack
4. canon mission / operating model / walker charters where relevant

If documents conflict, prefer the most local implementation artifact and record the ambiguity.

## Rules

### Stay inside scope

Do not redesign the architecture while implementing a narrow work item.

### Prefer deterministic code

If the capability can be expressed without AI behavior, do so.

### Respect contracts

Do not silently rename fields, change status semantics, or weaken scope semantics.

### Make degraded states explicit

Do not hide missing, partial, or degraded cases behind defaults.

### Keep modules small

Prefer simple pure helpers over sprawling abstractions.

### Write tests

Every meaningful implementation change should add or update tests.

## What to avoid

- speculative overengineering
- architecture drift
- hidden business rules
- silent fallback behavior
- fuzzy matching where exact resolution is required
- mixing interpretation logic into deterministic services

## Expected output per coding task

- code changes
- tests
- small notes on assumptions or ambiguities
- no unnecessary unrelated refactors

## Review checklist before submitting

- does this match the work item exactly?
- are all new contracts explicit and typed?
- are degraded states explicit?
- are tests present and meaningful?
- did I accidentally widen scope?

# Issue Planner Instruction

## Mission

Turn approved PRDs and ADR-backed design choices into small, testable, implementation-ready work items.

## Primary responsibilities

- split broad requirements into bounded slices
- preserve dependency order
- keep issues reviewable
- make acceptance criteria explicit
- route architecture ambiguity out of coding work

## Required reading order

1. linked PRD
2. linked ADRs
3. relevant local docs
4. `work_items/READY_CRITERIA.md`

## Decomposition rules

### Prefer contract-first sequencing

Create schema, fixture, and shared-foundation work before service logic when downstream code depends on them.

### Preserve architecture boundaries

Do not mix deterministic module work with walker, orchestrator, or UI implementation in one issue unless the outcome is intentionally cross-cutting and explicitly approved.

### Keep work small

A good work item should usually produce one coherent outcome that can be reviewed in one PR.

### Make dependencies explicit

Every work item should identify what must exist first.

### Make reviewable acceptance criteria

The reviewer should be able to answer pass or fail without inferring hidden intent.

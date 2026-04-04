# WI-1.1.2

## Linked PRD

PRD-1.1

## Purpose

Create a deterministic synthetic fixture pack for risk summary testing and replay.

## Scope

- synthetic hierarchy
- 5+ business dates
- VaR and ES values
- missing compare case
- zero prior case
- partial snapshot case
- fixture loader

## Out of scope

- service logic
- orchestrators
- UI

## Acceptance Criteria

- fixtures are deterministic
- loader is simple and documented
- fixtures support positive, edge, and degraded cases

## Suggested Agent

Coding Agent

## Review Focus

- determinism
- coverage of degraded scenarios
- simplicity

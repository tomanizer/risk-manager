# WI-1.1.5

## Linked PRD

PRD-1.1

## Purpose

Add rolling statistics and replay tests for the Risk Summary Service.

## Scope

- rolling mean
- rolling std
- rolling min/max
- history points used
- replay tests pinned by snapshot

## Out of scope

- new measures
- UI
- orchestrators

## Acceptance Criteria

- rolling stats use only available valid points
- replay tests stable across repeated runs
- degraded history handled explicitly

## Suggested Agent

Coding Agent

## Review Focus

- statistical correctness
- replayability
- no hidden time dependence

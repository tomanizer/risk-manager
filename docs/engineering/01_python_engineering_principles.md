# Python Engineering Principles

## Purpose

This document defines the implementation style expected from coding agents in this repository.

## Primary rule

Prefer clear, direct, deterministic Python over abstraction-heavy architecture.

## What good implementation looks like here

- one bounded slice at a time
- explicit data flow
- typed function boundaries where they matter
- clear degraded-case behavior
- small modules with obvious ownership
- predictable dependencies

## What to avoid

- speculative frameworks
- deep service-repository-manager-factory layering
- wrapper classes around standard libraries without a strong reason
- object-heavy inner loops for analytical code
- hidden fallbacks or magic behavior

## Deterministic-service bias

When implementing deterministic services:

- keep business logic in functions or small modules
- make canonical state transitions explicit
- keep replay-sensitive behavior visible
- do not bury core logic behind thin indirection layers

## Simplicity rule

If two approaches are both correct, prefer the one that is:

- easier to read
- easier to profile
- easier to test
- easier to replay deterministically

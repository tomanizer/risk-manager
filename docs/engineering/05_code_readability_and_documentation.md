# Code Readability And Documentation

## Purpose

This document defines readability expectations for implementation code in this repository.

## Readability is required

Performance-sensitive code must still be understandable.

The standard is:

- a reviewer can follow the data flow
- the hot path is obvious
- degraded behavior is obvious
- important assumptions are documented

## Preferred style

- short, well-named functions
- explicit function signatures
- small modules with one clear job
- public docstrings where behavior matters
- minimal but useful comments

## Comment rule

Comments should explain:

- why the implementation is shaped this way
- why a performance choice was made
- why a degraded or replay-sensitive behavior exists

Comments should not narrate obvious syntax.

## Documentation rule

Public deterministic service functions should usually document:

- purpose
- expected inputs
- degraded or failure behavior
- replay or snapshot assumptions where relevant

## Abstraction rule

Readable code is usually flatter and more direct than a heavily abstracted design.

Do not trade away readability in order to look more architected.

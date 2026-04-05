# Coding Quality Checklist

## Purpose

Use this checklist when acting as the coding agent or when reviewing coding-agent output.

## Scope and contract fidelity

- Did the change stay inside the assigned work item?
- Did it preserve PRD and ADR semantics?
- Are degraded and invalid cases explicit?

## Implementation quality

- Is the code direct rather than abstraction-heavy?
- Are function and module boundaries easy to follow?
- Are important assumptions documented briefly and clearly?
- Did the implementation use established libraries instead of reinvention?

## Test quality

- Do the tests prove the intended behavior?
- Do they cover edge and degraded cases that matter for the slice?
- Are the tests readable and maintainable?

## Failure patterns

- unnecessary layers of abstraction
- custom statistical or numerical code where a standard library would do
- hidden fallback behavior
- tests that are broad but low-signal

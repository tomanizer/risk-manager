# Review Triage And Escalation

## Purpose

This document explains how the PM agent should handle review feedback, especially GitHub bot comments, after a coding agent opens a draft PR.

## PM triage categories

### Must fix

Use this when the comment identifies a real issue in:

- correctness
- contract fidelity
- readiness or replay semantics
- boundary discipline
- missing tests
- hidden architecture drift

### Optional

Use this when the comment improves clarity or maintainability but is not required for the approved slice to be correct.

### Not applicable

Use this when the comment:

- asks for out-of-scope work
- misunderstands the PRD or work item
- pushes a refactor with no correctness reason
- conflicts with governed canon

## When to send work back to coding

Route back to coding when the finding can be fixed inside the approved slice without reopening canon.

## When to send work back to spec

Route back to spec when the review finding shows that canon is still missing:

- request meaning
- status model
- replay semantics
- domain terminology
- scope ownership

## When to stop the loop

Escalate to a human when:

- two reviewers identify conflicting but plausible canon interpretations
- a fix would require architecture redesign
- the PR scope is no longer the same slice the PM originally approved
- the repository needs a policy decision rather than an implementation decision

## Morning summary shape

The PM agent should classify each PR as:

- mergeable
- blocked
- needs decision
- superseded

A good summary says what happened, what was fixed, what remains open, and what the next action is.

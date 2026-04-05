# Slice Sizing And PR Strategy

## Purpose

This document defines what a good implementation slice looks like for the PM agent.

## One PR, one coherent outcome

The PM agent should prefer a PR that produces one reviewable outcome, such as:

- foundation contracts for one service
- one deterministic retrieval function
- one bounded doc clarification pack
- one replay harness slice

## Signs a slice is too broad

- it changes contracts, service behavior, and UI together
- it changes multiple work items without explicit approval
- it would be difficult for a review agent to summarize in one paragraph
- it requires multiple independent acceptance stories
- it touches unrelated target areas

## Safe combinations

The PM agent may combine closely coupled items in one PR only when:

- the dependency chain is explicit
- the combined scope is still one coherent outcome
- the target area remains narrow
- review expectations remain concrete

Typical safe example:

- contracts + deterministic fixtures + one local calendar helper for the same service foundation

## Split rules

Split work when:

- one slice includes both contract definition and interpretive logic
- one slice includes both retrieval and downstream summary logic
- one slice introduces a new cross-cutting concept and also tries to implement multiple consumers
- the review agent would need different review standards for different parts of the same PR

## Branching rule

- start each slice from fresh `main`
- create one fresh branch per bounded slice
- keep review-fix commits on the same branch only while they remain inside the approved slice

## Draft PR rule

The PM agent should prefer opening a draft PR early once the slice is coherent enough for external review comments to be useful.

Do not wait for a perfectly polished branch if the slice is already bounded and reviewable.

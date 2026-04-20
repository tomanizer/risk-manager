# PM Quality Checklist

## Purpose

Use this checklist when acting as the PM agent or when reviewing PM-agent output.

## Readiness judgment

- Did the PM agent identify the real blocker rather than pushing ambiguity downstream?
- Is the dependency story real, not assumed?
- Did the PM agent verify the next slice against the actual `work_items/` tree rather than only registry, roadmap, or PRD prose?
- Is the target area concrete enough to review?
- Did the PM agent say whether replay, evidence, or domain semantics are explicit enough?

## Slice quality

- Is the next PR one coherent outcome?
- Are out-of-scope reminders explicit?
- Are stop conditions concrete and useful?
- Would a coding agent know exactly when to halt and escalate?

## Brief quality

- Does the implementation brief describe what to build without redesigning canon?
- Does it avoid vague phrases like "handle edge cases appropriately"?
- Does it name the required tests or behaviors?
- Would a review agent be able to assess completion from the brief?

## Triage quality

- Did the PM agent classify review comments as `Must fix`, `Optional`, or `Not applicable`?
- Did the PM agent route canon gaps back to spec rather than asking coding to improvise?
- Did the PM agent preserve the bounded slice instead of accepting review-driven scope creep?

## Failure patterns

- generic "looks ready" language with no concrete blockers or scope
- naming a next WI range from a PRD or dashboard even though no corresponding work-item files exist
- target area described only at module-family level
- implementation brief that mixes current work with future work
- no distinction between code fix and canon fix
- asking the coding agent to decide semantics that belong in docs

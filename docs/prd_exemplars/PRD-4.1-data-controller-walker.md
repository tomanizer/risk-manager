# PRD-4.1: Data Controller Walker

## Variant
Walker PRD

## Purpose
Interpret trust, readiness, lineage, reconciliation, and false-signal conditions before deeper investigation proceeds.

## In scope
- trust assessment
- blocking vs cautionary classification
- false-signal interpretation
- handoff recommendation
- caveat generation

## Out of scope
- incident remediation
- analytical decomposition
- approvals
- free-form data access

## Core output
`TrustAssessment`
- target_scope
- target_type
- trust_state
- blocking_reasons
- cautionary_reasons
- supporting_findings
- false_signal_risk
- recommended_next_step
- evidence_refs

## Core rules
1. Material targets require trust assessment.
2. Blocking trust state prevents deeper interpretation unless degraded-run policy allows cautionary continuation.
3. All material trust findings require evidence refs.
4. The walker does not fix upstream issues.

## Acceptance criteria
- emits TRUSTED, CAUTION, BLOCKED, or UNRESOLVED states correctly
- emits explicit caveats and next-step hints
- uses typed control outputs only
- remains replayable and evidence-linked

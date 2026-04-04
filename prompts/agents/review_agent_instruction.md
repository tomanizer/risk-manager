# Review Agent Instruction

## Mission

Review implementation for scope fidelity, contract correctness, and risk-management usefulness.

The review agent is not only a code-style checker. It should review whether the delivered change still behaves like part of an AI-supported risk manager rather than a generic software artifact.

## Primary objectives

- check scope fidelity
- verify contract correctness
- verify degraded-state semantics
- verify test quality
- identify architecture leakage or drift

## Review lenses

### 1. Scope fidelity

Did the implementation stay inside the work item and PRD?

### 2. Contract fidelity

Did any schema, field, or status behavior drift from canon?

### 3. Determinism and replay

Is replay preserved where required?

### 4. Operational usefulness

Would a risk manager actually trust and use this output?

### 5. Test quality

Do tests cover positive, negative, edge, and degraded cases?

## What to flag hard

- silent contract changes
- hidden fallback behavior
- weak degraded-state handling
- replay-breaking logic
- fuzzy resolution where exact scope is required
- architecture invention slipped into a narrow implementation slice

## Expected output

- pass or fail recommendation
- material findings
- suggested fixes
- explicit note if the PR widened scope or drifted from canon

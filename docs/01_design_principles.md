# Design Principles

## Core principles

1. **Deterministic core, agentic edge**
   - calculations, thresholds, classifications, workflow state, and audit trails belong in deterministic services
   - walkers interpret and synthesize, but do not own canonical calculations

2. **Evidence-first**
   - material outputs must be traceable to typed source objects, workflow state, and versioned rules

3. **Replayability**
   - the same inputs, snapshots, and workflow versions must reproduce the same outputs

4. **Typed interfaces only**
   - no free-form data access from walkers or orchestrators

5. **KISS and YAGNI**
   - build the smallest useful bounded capability slice first
   - avoid speculative abstractions

6. **Separation of concerns**
   - modules do not become walkers
   - walkers do not become modules
   - orchestrators do not become policy engines
   - UI does not recompute business logic

7. **Trust before interpretation**
   - material workflows should pass through trust / readiness validation before deeper interpretation

8. **Challenge before governance output**
   - significant outputs should be challenged before sign-off or committee use

9. **No hidden policy or side effects**
   - policy rules must be explicit and versioned
   - services should not silently mutate upstream truth

# Repo Drift Monitoring

## Purpose

This document defines the repository's repo-wide drift-monitoring control.

The purpose of this control is to detect coherence decay across canon, prompts, work items, registry state, implementation, tests, dependencies, and developer tooling before that drift turns into incorrect PM routing, weak PRDs, bad implementation assumptions, or contradictory review standards.

This role is not a replacement for PM, coding, or review. It is a periodic governance control that helps keep the repository internally coherent over time.

## Mission

Detect repo-wide drift early and route it to the right owner with evidence.

The drift monitor should act like an architecture and governance auditor for the whole repository, not like a second coding agent and not like a PR reviewer looking only at one slice.

## What the drift monitor audits

### Canon coherence

Check whether repository canon stays internally consistent across:

- `docs/`
- ADRs
- PRDs
- prompt instructions
- work-item conventions

### Duplication and source-of-truth clarity

Check whether the same concept appears in multiple places and whether that duplication is:

- sanctioned and clearly labeled
- accidental and now diverging
- contradictory
- so repetitive that it weakens focus

### Delivery-framework coherence

Check whether:

- prompt instructions still match governed delivery canon
- work-item standards still match PM and review expectations
- role boundaries remain explicit
- the agent relay is being preserved rather than collapsed

### Registry and catalog coherence

Check whether catalogs, registries, README files, and status markers still reflect the repository's actual state well enough to guide future work safely.

### Tooling and operational hygiene

Check whether the repository's operational scaffolding still matches the real implementation state, for example:

- project packaging and metadata
- dependency declarations versus actual imports and runtime use
- lint, format, type-check, and test controls
- CI checks versus local standards
- local test harness workarounds that exist only because packaging or config is missing

### Architecture and implementation drift

Check for signs that implementation is eroding the intended boundaries:

- deterministic services owning interpretation instead of canonical facts
- walkers owning canonical logic
- orchestrators becoming policy engines
- UI or presentation layers recomputing governed logic

### Repository hygiene and prose quality

Check whether important docs are becoming:

- stale
- contradictory
- bloated
- vague
- directionless
- overly fluffy relative to the repository's precision standard

Also check whether the repository is drifting into instruction sprawl, where the same operational rules are restated across too many agent or tool surfaces without a clear primary source.

## What the drift monitor does not own

- merge decisions
- routine PR review
- direct implementation of follow-up fixes unless explicitly reassigned
- canon rewrites without PM or human approval
- speculative redesign of architecture

## Position in the operating model

The drift monitor is outside the normal implementation handoff chain.

The normal chain remains:

1. PM
2. issue planner or PRD/spec work when needed
3. coding
4. review
5. human merge decision

The drift monitor runs as a separate periodic control and hands findings to the PM agent or a human for triage.

## Core operating rules

### Evidence first

Do not report drift based on vague discomfort.

Every material finding should name the conflicting artifacts, the exact contradiction or duplication pattern, and why that matters operationally.

Where a deterministic scanner exists, run it before free-form repo reading and use its structured output as the first evidence surface.

### Distinguish sanctioned duplication from unhealthy duplication

Some duplication is legitimate when one artifact is clearly a short-form summary, index, exemplar, or local adaptation of a broader canon document.

Duplication becomes a real drift finding when:

- there is no declared primary artifact
- the duplicate copy has started to diverge materially
- the local version contradicts the broader contract without saying so
- the repetition is creating ambiguity about what later agents should trust

The same rule applies to operational instructions, such as repeated freshness rules, role boundaries, or workflow constraints spread across several agent surfaces.

### Prefer routing over rewriting

The drift monitor should normally recommend where work should go next rather than trying to fix everything directly.

### Stay repo-wide

This role should look for patterns that cross files, folders, or operating layers. It should not devolve into line-level nitpicking better handled by review.

### Preserve bounded ownership

A finding is only useful if it identifies the right owner or execution route:

- PM
- PRD author
- methodology/spec
- coding
- review
- repository maintenance
- human decision

The drift monitor should also state whether the problem is:

- canon drift
- implementation drift
- tooling drift
- operational-instruction drift
- maturity or status drift

## Severity model

### Critical

Use when drift could cause the repository to make or approve wrong work, for example:

- contradictory canonical semantics
- boundary rules that conflict across governance sources
- duplicate source-of-truth claims
- stale instructions that could drive incorrect implementation behavior
- CI or dependency declarations that materially misrepresent what the repository requires or verifies
- registry or maturity markers that materially contradict implemented, tested reality

### Major

Use when drift is materially raising future execution risk, for example:

- duplicated concepts with partial divergence
- registry or catalog state that is no longer trustworthy enough for planning
- prompt instructions lagging canon in a way that could misroute work
- sprawling documentation that obscures the real contract
- tooling configuration gaps that force local hacks or weaken development discipline
- dependencies that are declared as foundational but are not actually used yet

### Minor

Use when the problem is real but not yet likely to cause incorrect implementation, for example:

- naming inconsistency
- light duplication with no semantic divergence yet
- bloated prose or weak information architecture
- README or index drift that hurts navigation more than correctness
- low-risk instruction overlap that is still semantically aligned

## Routing rules

### Route to PM

Use when the finding affects readiness, sequencing, review triage, ownership, or work-item discipline.

### Route to PRD author

Use when the implementation contract is duplicated, unclear, or drifting relative to canon.

### Route to methodology/spec

Use when market-risk concepts, terminology, caveats, or methodological distinctions are unclear or conflicting.

### Route to coding

Use when the canonical answer is already clear and the problem is an implementation drift or boundary violation that can be corrected without reopening canon.

### Route to repository maintenance

Use this label in the report when the problem is primarily packaging, dependency, CI, lint, format, or type-check hygiene. PM should usually turn this into a bounded work item rather than asking a spec agent to resolve it.

### Route to review

Use when the finding indicates a review checklist or review prompt gap rather than a missing contract.

### Route to human

Escalate when two plausible source-of-truth candidates conflict, when a policy choice is needed, or when fixing the drift would redesign the operating model.

## Recommended cadence

Run the drift monitor:

- on current `main`
- before major planning resets
- after substantial canon or prompt-pack changes
- on a regular periodic cadence such as weekly or nightly, depending on repo activity

Do not treat it as a mandatory gate on every ordinary PR unless the repository later proves that such a gate is worth the noise.

## Deterministic prechecks

The repo-health loop should prefer deterministic prechecks before LLM synthesis where possible.

Initial deterministic scanner:

- `scripts/drift/check_references.py`
- `scripts/drift/check_registry_alignment.py`

Recommended usage:

```bash
python scripts/drift/check_references.py --root . --output artifacts/drift/reference_integrity.json
python scripts/drift/check_registry_alignment.py --root . --output artifacts/drift/registry_alignment.json
```

These scanners check:

- tracked text files for broken internal file references
- the current-state registry for mismatches between declared implementation status and the repository's actual module roots and registered implementation paths

They let the drift monitor start from machine-generated evidence about stale paths, deleted files, missing targets, and maturity/status drift in the registry.

## Required output shape

Every drift-monitor pass should return:

1. overall repo health status: `HEALTHY`, `WATCH`, or `DRIFTING`
2. findings by severity
3. evidence for each material finding
4. drift class for each material finding
5. why each finding matters
6. owner and routing recommendation
7. whether any duplication is sanctioned and acceptable
8. the smallest sensible next action for each major or critical item

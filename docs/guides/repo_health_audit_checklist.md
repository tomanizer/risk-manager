# Repo Health Audit Checklist

## Purpose

Use this checklist when acting as the drift monitor or when reviewing a repo-health audit.

The goal is to detect repository-level coherence drift, not to re-review one implementation slice.

## Evidence rule

- Does each finding cite the specific files that create the problem?
- Does the finding explain the contradiction, duplication, or drift explicitly?
- Does the report separate hard drift from stylistic preference?

## Canon coherence

- Do core canon documents agree on architecture boundaries?
- Do short-form and long-form canon documents clearly identify which is the primary reference?
- Do PRDs still align with repo-wide canon and linked ADRs?
- Do prompts and guides still reinforce the same governed operating model?
- Are important caveats preserved consistently rather than dropped in shorter summaries?

## Duplication and source-of-truth clarity

- Is the same concept repeated in multiple places?
- If so, is one source clearly primary and the others clearly secondary?
- Have duplicated definitions diverged in meaning, scope, or caveats?
- Are there multiple active versions of the same PRD, charter, or rule without explicit lineage?
- Is repeated prose making it harder to tell which artifact later agents should trust?

## Delivery and role-boundary coherence

- Do `AGENTS.md`, delivery docs, prompts, and workflow guides still describe the same agent model?
- Are PM, coding, review, PRD/spec, and drift-monitor responsibilities still distinct?
- Has any document started to collapse planning, coding, review, and merge judgment into one pass?
- Do review and PM materials still route canon gaps back to spec instead of pushing them into coding?

## Registry and catalog coherence

- Does the current-state registry still match the repository's declared components and maturity?
- Do README files, catalogs, and indexes still reflect the real structure of the repo?
- Are roadmap, registry, and implementation artifacts directionally aligned?
- Are there stale status markers, missing entries, or misleading labels that could misroute future work?
- Does declared maturity match implemented and tested reality, especially for foundation slices that already exist?

## Architecture and technical integrity

- Do modules, walkers, orchestrators, and UI artifacts still respect their intended boundaries?
- Is canonical logic staying in deterministic services?
- Are walkers consuming typed outputs rather than becoming hidden computation layers?
- Are orchestrators avoiding policy or calculation ownership?
- Are tests and fixtures still aligned with the canonical contracts they are supposed to prove?

## Tooling and dependency hygiene

- Does the repo have the packaging and config files expected for its current maturity?
- Are test, lint, format, and type-check standards all declared and enforced consistently?
- Is CI verifying the same quality bar that local docs and agent instructions assume?
- Are there local harness hacks that exist only because packaging or config is missing?
- Do declared dependencies match actual imports and current implementation reality?
- Are there heavy or strategic dependencies declared long before the code actually uses them?

## Instruction-surface coherence

- Are shared operational rules repeated across many agent/tool instruction files?
- If repeated, is there a clear primary source for those rules?
- Have the repeated versions started to drift in wording or meaning?
- Are tool-specific instructions staying subordinate to repo canon rather than becoming shadow policy?

## Documentation quality and focus

- Are important documents concise enough to stay governable?
- Has prose become repetitive, fluffy, or vague enough to obscure the actual contract?
- Are open questions explicit where ambiguity remains?
- Are local docs focused on local implementation truth rather than re-explaining the whole repository?

## Hygiene and freshness

- Are links, file references, and named artifacts still valid?
- Are old files superseded explicitly rather than left as ambiguous active guidance?
- Are deprecated or draft artifacts labeled clearly enough?
- Has a summary, prompt, or checklist gone stale relative to current canon?

## Severity test

- Would this issue cause wrong implementation, wrong review, or wrong PM routing now?
- Would it more likely cause confusion soon if left alone?
- Is it mostly a navigation or readability problem?
- Is it primarily canon drift, tooling drift, operational-instruction drift, or maturity/status drift?

## Required audit output

A good repo-health audit should return:

1. overall health status
2. critical findings
3. major findings
4. minor findings
5. drift class for each material finding
6. sanctioned duplication noted as acceptable
7. recommended owner for each material finding
8. smallest next step for each critical or major finding to restore coherence

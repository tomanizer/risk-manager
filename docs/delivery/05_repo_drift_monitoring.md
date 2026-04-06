# Repo Drift Monitoring

## Purpose

Detect coherence decay across canon, prompts, work items, registry state, implementation, tests, dependencies, and developer tooling before that drift turns into incorrect PM routing, weak PRDs, bad implementation assumptions, or contradictory review standards.

This is a periodic governance control, not a replacement for PM, coding, or review.

## Mission

Detect repo-wide drift early and route it to the right owner with evidence.

The drift monitor acts like an architecture and governance auditor for the whole repository, not like a second coding agent and not like a PR reviewer looking only at one slice.

## System architecture

The system has two layers:

1. **Deterministic scanners** -- machine-checkable evidence about specific drift indicators (fully wired in CI)
2. **Audit synthesis layer** -- an LLM drift-monitor pass that uses scanner output as its first evidence surface (**Phase 2: not yet wired in CI**)

The deterministic suite is coordinated by `agent_runtime/drift/drift_suite.py` and run via `scripts/drift/run_all.py`.

## Running the suite

### Locally

```bash
python scripts/drift/run_all.py \
  --root . \
  --artifact-dir artifacts/drift \
  --output artifacts/drift/latest_report.json \
  --summary-output artifacts/drift/summary.md
```

Always run against current `main`:

```bash
git fetch origin && git switch main && git pull --ff-only origin main
```

Add `--fail-on-findings` to exit non-zero when net-new findings remain after baseline filtering.

### CI

`.github/workflows/drift-monitor.yml` runs:

- **Nightly at 02:00 UTC** (every day including weekends), to catch findings from overnight agent runs
- **On push to `main`** for relevant paths
- **On pull requests labeled `agent-authored`**, posting a non-blocking summary comment
- **On manual dispatch** (`workflow_dispatch`)
- **Via `workflow_call`**, so downstream workflows (e.g. the relay) can invoke it as a reusable step

When triggered by a non-PR event it:

1. Runs the deterministic suite
2. Writes the markdown summary into the GitHub Actions job summary
3. Renders an issue body from `latest_report.json`
4. Creates or updates a stable "Repo Health Drift Report" issue when net-new findings exist (identified by title + `<!-- drift-monitor-issue -->` marker)
5. Closes that issue automatically when the suite returns to zero net-new findings
6. Creates a `work_items/ready/drift-fix-<date>.md` work item when auto-remediable findings are present
7. Uploads all drift artifacts

When triggered by a PR event it posts a summary comment on the PR (never blocks merge).

### Recommended cadence

The scheduled nightly run covers the baseline cadence. Additionally:

- Before major planning resets
- After substantial canon or prompt-pack changes
- After every agent coding run (via `workflow_call` from the relay CI)

## Scanner inventory

### Architecture boundaries

**Implementation:** `agent_runtime/drift/architecture_boundaries.py`
**CLI:** `scripts/drift/check_architecture_boundaries.py`
**Drift class:** implementation drift
**Typical owner:** coding

Checks:
- Import-boundary violations between `src/modules/`, `src/walkers/`, `src/orchestrators/`, UI surfaces, and `agent_runtime/`
- Module code importing walker, orchestrator, or runtime surfaces
- Walker code importing orchestrator or runtime surfaces
- Orchestrator code importing runtime surfaces
- UI code importing walker, orchestrator, or runtime surfaces
- Runtime code importing module, walker, or orchestrator surfaces

Does not check semantic architecture quality beyond explicit import edges, runtime wiring within allowed imports, or non-Python coupling.

### Canon lineage

**Implementation:** `agent_runtime/drift/canon_lineage.py`
**CLI:** `scripts/drift/check_canon_lineage.py`
**Drift class:** canon drift
**Typical owner:** PRD author, PM, repository maintenance

Checks:
- Multiple live versioned canon documents in the same lineage group
- Active versioned canon documents missing `Supersedes` metadata for archived predecessors
- Mismatched `Supersedes` references
- Active execution surfaces still pointing at archived PRDs

Does not check whether a successor is substantively better, whether non-versioned documents are semantically duplicative, or whether archived references in narrative docs are legitimate.

### Dependency hygiene

**Implementation:** `agent_runtime/drift/dependency_hygiene.py`
**CLI:** `scripts/drift/check_dependency_hygiene.py`
**Drift class:** tooling drift, operational-instruction drift
**Typical owner:** repository maintenance

Checks:
- Runtime imports not declared in `pyproject.toml`
- Runtime dependencies declared only in optional extras instead of base
- Test/tooling imports not declared in dependency metadata
- Workflow tools (`pytest`, `ruff`, `mypy`) missing from the `dev` extra
- Legacy `requirements.txt` instruction drift

Does not check whether a dependency is the right choice, whether version pins are optimal, or extra splitting.

### Instruction surfaces

**Implementation:** `agent_runtime/drift/instruction_surfaces.py`
**CLI:** `scripts/drift/check_instruction_surfaces.py`
**Drift class:** operational-instruction drift
**Typical owner:** repository maintenance

Checks:
- Missing role-surface pairs between `.github/agents/` and `prompts/agents/`
- Stale README inventories for instruction packs
- Missing `AGENTS.md` references in external instruction surfaces
- Incomplete or out-of-order freshness-rule triads
- Drift-monitor surfaces that stop pointing to `scripts/drift/run_all.py`

Does not check prompt quality, global minimality, or whether semantically aligned overlap should be deduplicated.

### Reference integrity

**Implementation:** `agent_runtime/drift/reference_integrity.py`
**CLI:** `scripts/drift/check_references.py`
**Drift class:** canon drift, operational-instruction drift
**Typical owner:** PM, repository maintenance

Checks:
- Broken internal file references in tracked text surfaces
- References that escape the repository root
- Stale references to deleted or moved paths

Sanctioned generated artifact outputs listed in `artifacts/` READMEs and ignored by `.gitignore` are not reported as broken.

Does not check whether a reference points to the right source of truth.

### Registry alignment

**Implementation:** `agent_runtime/drift/registry_alignment.py`
**CLI:** `scripts/drift/check_registry_alignment.py`
**Drift class:** maturity or status drift
**Typical owner:** PM

Checks:
- Active registry entries missing expected implementation paths (modules, walkers, orchestrators)
- Inactive entries that already have implementations
- Implemented subcomponents with no declared path (modules only)
- Unregistered roots under `src/modules/`, `src/walkers/`, and `src/orchestrators/`

ID-to-directory mapping: `MOD-RISK-ANALYTICS` → `src/modules/risk_analytics`, `WALKER-QUANT` → `src/walkers/quant`, `ORCH-LIMIT-BREACH` → `src/orchestrators/limit_breach`. <!-- drift-ignore -->

Does not check architectural correctness inside components or whether implementation is complete enough for declared semantics.

### Surface liveness

**Implementation:** `agent_runtime/drift/surface_liveness.py`
**CLI:** `scripts/drift/check_surface_liveness.py`
**Drift class:** operational-instruction drift, implementation drift
**Typical owner:** repository maintenance, coding

Checks:
- Active text surfaces referencing `python -m <module>` entrypoints that don't exist in the repo
- Active code importing from legacy-marked repo surfaces (module path segments named `archive`, `archived`, `deprecated`, or `legacy`)

Does not check whether a module entrypoint is the right design, whether non-legacy imports are architecturally correct, or orphaned module roots (covered by registry alignment).

## Artifacts

Per-scanner JSON:
- `artifacts/drift/architecture_boundaries.json`
- `artifacts/drift/canon_lineage.json`
- `artifacts/drift/dependency_hygiene.json`
- `artifacts/drift/instruction_surfaces.json`
- `artifacts/drift/reference_integrity.json`
- `artifacts/drift/registry_alignment.json`
- `artifacts/drift/surface_liveness.json`

Aggregate:
- `artifacts/drift/latest_report.json`
- `artifacts/drift/summary.md`
- `artifacts/drift/issue_body.md` (rendered for issue automation)

Tracked baseline:
- `artifacts/drift/baseline.json`

Generated JSON reports should usually stay uncommitted unless a human explicitly wants to preserve one as review evidence.

### Aggregate report semantics

`latest_report.json` contains:
- `scans`: per-scanner rollups
- `findings`: net-new findings after baseline filtering
- `waived_findings`: findings still present but covered by baseline
- `stats.total_findings`: raw total before baseline filtering
- `stats.new_findings`: active unwaived findings
- `stats.waived_findings`: accepted-but-still-present findings

Use `new_findings` for alerting, `waived_findings` for known debt tracking, `total_findings` for overall burden awareness.

## Baseline model

### Purpose

The baseline exists for accepted drift that is already understood, intentionally deferred, still worth keeping visible, but not useful to re-alert as net-new every scheduled run.

### File

`artifacts/drift/baseline.json`

### Shape

```json
{
  "version": 1,
  "allowed_findings": [
    {
      "scan_name": "...",
      "signature": "...",
      "rationale": "...",
      "issue": "#123",
      "expires_on": "2025-06-01"
    }
  ]
}
```

Each scanner has a deterministic finding signature derived from stable fields (kind + scanner-specific identity fields). This lets the suite distinguish the same known drift recurring from a genuinely new finding.

### When to baseline

Baseline a finding only when:
- It is understood
- It has a clear owner
- It has a known remediation path
- Repeated re-alerting would add little value

Always include a rationale, and strongly prefer linking an issue and setting an expiry date.

`expires_on` is enforced: once the date passes, the entry no longer waives the finding and the finding resurfaces as net-new. This prevents the baseline from becoming a permanent suppress list.

### Bad patterns

- Bulk-baselining a whole scanner
- Vague rationales like "known" or "later"
- Baselining before anyone agrees the finding is real
- Baselining active policy conflicts

## What the drift monitor audits

### Canon coherence
Whether canon stays internally consistent across `docs/`, ADRs, PRDs, prompt instructions, and work-item conventions.

### Duplication and source-of-truth clarity
Whether duplication is sanctioned (labeled summary, index, exemplar, or local adaptation) versus accidental, diverging, contradictory, or so repetitive it weakens focus.

### Delivery-framework coherence
Whether prompt instructions match governed delivery canon, work-item standards match PM and review expectations, role boundaries remain explicit, and the agent relay is preserved.

### Registry and catalog coherence
Whether catalogs, registries, README files, and status markers still reflect actual state well enough to guide future work safely.

### Tooling and operational hygiene
Whether packaging, dependency declarations, lint/format/type-check/test controls, and CI checks match real implementation state.

### Architecture and implementation drift
Whether implementation is eroding intended boundaries (deterministic services owning interpretation, walkers owning canonical logic, orchestrators becoming policy engines, UI layers recomputing governed logic).

### Repository hygiene and prose quality
Whether important docs are becoming stale, contradictory, bloated, vague, directionless, or drifting into instruction sprawl.

## What the drift monitor does not own

- Merge decisions
- Routine PR review
- Direct implementation of fixes (unless explicitly reassigned)
- Canon rewrites without PM or human approval
- Speculative redesign of architecture

## Severity model

**Critical** -- drift could cause the repository to make or approve wrong work: contradictory canonical semantics, conflicting boundary rules, duplicate source-of-truth claims, stale instructions driving incorrect behavior, CI/dependency declarations that misrepresent what the repo requires, registry markers that materially contradict reality.

**Major** -- drift is materially raising future execution risk: duplicated concepts with partial divergence, untrustworthy registry state, prompt instructions lagging canon, sprawling documentation, tooling gaps forcing local hacks, phantom dependencies.

**Minor** -- the problem is real but not yet likely to cause incorrect implementation: naming inconsistency, light duplication with no semantic divergence, bloated prose, README drift affecting navigation not correctness, low-risk instruction overlap that is still semantically aligned.

## Routing rules

| Route to | When |
|---|---|
| PM | Affects readiness, sequencing, review triage, ownership, or work-item discipline |
| PRD author | Implementation contract is duplicated, unclear, or drifting relative to canon |
| Methodology/spec | Market-risk concepts, terminology, caveats, or methodological distinctions are unclear or conflicting |
| Coding | Canonical answer is clear, problem is implementation drift or boundary violation |
| Repository maintenance | Primarily packaging, dependency, CI, lint, format, or type-check hygiene |
| Review | Finding indicates a review checklist or review prompt gap |
| Human | Two plausible source-of-truth candidates conflict, a policy choice is needed, or fixing would redesign the operating model |

Every finding should also state its drift class: canon, implementation, tooling, operational-instruction, or maturity/status drift.

## Required output shape

Every drift-monitor pass should return:
1. Overall repo health status: `HEALTHY`, `WATCH`, or `DRIFTING`
2. Findings by severity
3. Evidence for each material finding
4. Drift class for each material finding
5. Why each finding matters
6. Owner and routing recommendation
7. Whether any duplication is sanctioned and acceptable
8. The smallest sensible next action for each major or critical item

## Noise reduction

### Inline suppress annotation

Add `<!-- drift-ignore -->` at the end of any line in a tracked text file to suppress all reference integrity and dependency hygiene findings from that line. Use this when a reference is illustrative (example code, template, future placeholder) rather than normative.

```markdown
See `scripts/drift/run_all.py` for the command. <!-- drift-ignore -->
```

Do not use `<!-- drift-ignore -->` to suppress real drift. Prefer a baseline entry with a rationale and expiry date for known findings.

### Fenced code blocks

`reference_integrity` and `dependency_hygiene` skip all reference and stale-guidance extraction inside fenced code blocks (triple-backtick or triple-tilde). Example commands in documentation are illustrative, not normative path references.

## LLM synthesis layer (Phase 2)

The system documentation describes a second layer where an LLM drift-monitor agent reads `latest_report.json` alongside key repo surfaces (`AGENTS.md`, registry, recent PRs) and produces:

- Thematic summary of drift patterns
- Root-cause hypotheses
- Prioritised fix suggestions

This layer is **not yet wired into CI**. When implemented it will run as a separate, lower-frequency workflow job (`drift-synthesis`, weekly schedule) and append a synthesis comment to the open drift issue rather than blocking the deterministic pipeline.

The drift-monitor agent role is already defined in `.github/agents/drift-monitor.agent.md` and `prompts/agents/drift_monitor_agent_instruction.md`.

## Extending the system

When adding a new deterministic scanner:

1. Implementation module under `agent_runtime/drift/`
2. CLI entrypoint under `scripts/drift/`
3. Stable finding shapes and signatures
4. Focused unit tests in `tests/unit/agent_runtime/`
5. Wire into `drift_suite.py` (`_SCANNERS` and `_SIGNATURE_FIELDS`)
6. Add artifact path to `artifacts/drift/README.md`
7. Update workflow artifact upload if a new per-scanner JSON is produced

Reference implementation: `agent_runtime/drift/surface_liveness.py` (`surface_liveness` scanner), added via PR #88.

Good deterministic scanners should operate on clearly defined repo surfaces, emit evidence-rich findings, avoid fuzzy heuristics that create noise, and degrade explicitly when required files are missing or malformed.

## Debugging

**Scanner suddenly reports many findings:** Check whether a shared path moved, a README inventory is stale, a baseline signature stopped matching (finding shape changed), or the repo was run from stale local state.

**Suite reports findings but the issue did not update:** Check workflow permissions, `actions/github-script` execution, whether the issue marker changed, issue lookup pagination, or whether the job failed before the upsert step.

**Suite reports no findings when expected:** Check whether the finding is currently baselined (including whether `expires_on` is still in the future), the scanner is wired into `drift_suite.py`, the target file surface is in the scanned path, the line has a `<!-- drift-ignore -->` annotation, or a generated path is intentionally sanctioned.

**False positive from a backtick in documentation:** If the path is inside a fenced code block, `reference_integrity` will skip it automatically. If the path is outside a code block but illustrative, add `<!-- drift-ignore -->` to that line or add a baseline entry with rationale.

**Baseline entry no longer suppressing a finding:** The `expires_on` date has passed. Either extend the expiry date with an updated rationale, or fix the underlying drift.

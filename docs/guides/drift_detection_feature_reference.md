# Drift Detection Feature Reference

## Purpose

This document explains the implemented drift-detection features in concrete operational terms.

Use it when you need to understand:

- what the deterministic drift suite actually runs
- what each scanner checks and does not check
- what artifacts are generated
- how baseline waivers work
- how the scheduled workflow turns findings into a stable GitHub issue

This is a feature reference for the implemented drift-detection system. It is not a replacement for the higher-level governance policy in `docs/delivery/05_repo_drift_monitoring.md`.

## System model

The repository now has two layers of repo-health control:

1. deterministic scanners
2. an audit synthesis layer

The deterministic layer exists to produce machine-checkable evidence before an LLM drift-monitor pass starts reading the repo free-form.

The current deterministic suite is coordinated by:

- `scripts/drift/run_all.py`
- `agent_runtime/drift/drift_suite.py`

The suite:

- runs the configured deterministic scanners
- writes one JSON artifact per scanner
- writes one aggregate JSON report
- writes one markdown summary
- applies the tracked baseline in `artifacts/drift/baseline.json`
- reports only net-new findings as active drift

This gives the drift monitor a stable input surface and reduces hallucinated or inconsistent repo-health reporting.

## Current scanner inventory

### Architecture boundaries

Entry point:

- `scripts/drift/check_architecture_boundaries.py`

Implementation:

- `agent_runtime/drift/architecture_boundaries.py`

Checks:

- deterministic import-boundary violations between `src/modules/`, `src/walkers/`, `src/orchestrators/`, UI surfaces, and `agent_runtime/`
- module code importing walker, orchestrator, or runtime surfaces
- walker code importing orchestrator or runtime surfaces
- orchestrator code importing runtime surfaces
- UI code importing walker, orchestrator, or runtime surfaces
- runtime code importing module, walker, or orchestrator surfaces

Primary drift class:

- implementation drift

Typical owner:

- coding

Does not check:

- semantic architecture quality beyond explicit import edges
- runtime wiring that stays within allowed imports but still has poor responsibilities
- non-Python coupling such as shell scripts, config wiring, or documentation-only boundary drift

### Canon lineage

Entry point:

- `scripts/drift/check_canon_lineage.py`

Implementation:

- `agent_runtime/drift/canon_lineage.py`

Checks:

- multiple live versioned canon documents in the same lineage group
- active versioned canon documents that fail to declare the archived predecessor they supersede
- active versioned canon documents whose `Supersedes` metadata points at the wrong predecessor
- active execution surfaces that still point at archived PRDs instead of the active canon document

Primary drift class:

- canon drift

Typical owner:

- PRD author
- PM
- repository maintenance

Does not check:

- whether the successor document is substantively better than the predecessor
- whether two non-versioned documents are semantically duplicative
- whether an archived reference is historically useful in narrative or retrospective documentation outside execution surfaces

### Dependency hygiene

Entry point:

- `scripts/drift/check_dependency_hygiene.py`

Implementation:

- `agent_runtime/drift/dependency_hygiene.py`

Checks:

- runtime imports not declared in `pyproject.toml`
- runtime dependencies declared only in optional extras instead of base dependencies
- test or tooling imports not declared in dependency metadata
- workflow tools such as `pytest`, `ruff`, or `mypy` missing from the `dev` extra
- legacy dependency-instruction text that still treats `requirements.txt` as canonical instead of `pyproject.toml`

Primary drift class:

- tooling drift
- operational-instruction drift

Typical owner:

- repository maintenance

Does not check:

- whether a dependency is semantically the right choice
- whether a dependency version pin is optimal
- whether a dependency should be split into multiple extras

### Instruction surfaces

Entry point:

- `scripts/drift/check_instruction_surfaces.py`

Implementation:

- `agent_runtime/drift/instruction_surfaces.py`

Checks:

- missing role-surface pairs between `.github/agents/` and `prompts/agents/`
- stale README inventories for those instruction packs
- missing `AGENTS.md` references in external instruction surfaces
- incomplete or out-of-order freshness-rule triads
- drift-monitor surfaces that stop pointing to `scripts/drift/run_all.py`

Primary drift class:

- operational-instruction drift

Typical owner:

- repository maintenance

Does not check:

- whether a prompt is persuasive or well-written
- whether agent instructions are globally minimal
- whether semantically aligned overlap should be deduplicated

### Reference integrity

Entry point:

- `scripts/drift/check_references.py`

Implementation:

- `agent_runtime/drift/reference_integrity.py`

Checks:

- broken internal file references in tracked text surfaces
- references that escape the repository root
- stale references to deleted or moved repo paths

Primary drift class:

- canon drift
- operational-instruction drift

Typical owner:

- PM
- repository maintenance

Special behavior:

- sanctioned generated artifact outputs listed in `artifacts/` READMEs and ignored by `.gitignore` are not reported as broken references

Does not check:

- whether the referenced file is the right source of truth
- whether a reference points to an archived file that is technically present but semantically wrong

### Registry alignment

Entry point:

- `scripts/drift/check_registry_alignment.py`

Implementation:

- `agent_runtime/drift/registry_alignment.py`

Checks:

- active registry entries missing their expected implementation paths
- inactive registry entries that already have implementation roots
- implemented subcomponents with no declared path
- module roots under `src/modules/` that are not represented in the registry

Primary drift class:

- maturity or status drift

Typical owner:

- PM

Does not check:

- deeper architectural correctness inside the module
- whether a module implementation is complete enough for its declared semantics

## Aggregate suite behavior

### Entry point

Run the full deterministic suite with:

```bash
python scripts/drift/run_all.py --root . --artifact-dir artifacts/drift --output artifacts/drift/latest_report.json --summary-output artifacts/drift/summary.md
```

### What the suite writes

Per-scanner JSON artifacts:

- `artifacts/drift/architecture_boundaries.json`
- `artifacts/drift/canon_lineage.json`
- `artifacts/drift/dependency_hygiene.json`
- `artifacts/drift/instruction_surfaces.json`
- `artifacts/drift/reference_integrity.json`
- `artifacts/drift/registry_alignment.json`

Aggregate outputs:

- `artifacts/drift/latest_report.json`
- `artifacts/drift/summary.md`
- `artifacts/drift/issue_body.md` when rendered for issue automation

Tracked baseline:

- `artifacts/drift/baseline.json`

### Aggregate report semantics

`latest_report.json` contains:

- `scans`: per-scanner rollups
- `findings`: net-new findings after baseline filtering
- `waived_findings`: findings still present but covered by the tracked baseline
- `stats.total_findings`: raw total across scanners before baseline filtering
- `stats.new_findings`: active unwaived findings
- `stats.waived_findings`: accepted-but-still-present findings

The drift-monitor workflow and issue automation should treat `new_findings` as the main alerting signal.

### Why the suite exists

The suite solves four practical problems:

1. scanners should run together with one canonical entrypoint
2. baseline filtering should happen once in a governed way
3. issue automation should not need to know scanner internals
4. drift-monitor prompts should point to one deterministic precheck command, not a growing list of hand-run scripts

## Baseline model

### Purpose

The baseline exists for accepted drift that is:

- already understood
- intentionally deferred
- still worth keeping visible
- not useful to re-alert as net-new every scheduled run

The baseline is not a place to hide unknown noise.

### File

- `artifacts/drift/baseline.json`

### Shape

The file contains:

- `version`
- `allowed_findings`

Each allowed finding should include:

- `scan_name`
- `signature`
- `rationale`

Optional fields:

- `issue`
- `expires_on`

### Signature semantics

Each scanner has a deterministic finding signature derived from stable fields.

Examples:

- dependency hygiene: kind + dependency + source path
- instruction surfaces: kind + source path + related paths
- reference integrity: kind + source file + line + reference
- registry alignment: kind + component + implementation path + registry path

This lets the suite distinguish:

- the same known drift recurring
- a genuinely new finding from the same scanner

### Good baseline usage

Use the baseline when:

- a finding already has a bounded remediation issue
- the fix is intentionally sequenced later
- repeated scheduled alerts would add noise without changing behavior

Do not baseline findings when:

- the finding is not yet understood
- there is no owner
- the finding reflects an active policy conflict
- the finding is severe enough that a silent waiver would be misleading

## GitHub workflow behavior

### Workflow

- `.github/workflows/drift-monitor.yml`

### Current workflow steps

The workflow:

1. checks out the repo
2. installs the repo and dev tooling
3. runs the deterministic suite
4. writes the markdown summary into the GitHub Actions job summary
5. renders an issue body from `latest_report.json`
6. creates or updates a stable `Repo Health Drift Report` issue when net-new findings exist
7. closes that issue when the suite returns to zero net-new findings
8. uploads all drift artifacts

### Stable issue contract

The issue body contains a hidden marker:

- `<!-- drift-monitor-issue -->`

The workflow uses that marker plus the fixed issue title to avoid confusing the repo-health issue with unrelated issues.

The workflow now paginates through repository issues instead of inspecting only the first page, so the stable issue lookup remains correct in larger repositories.

### Why issue automation matters

Artifacts alone are passive. A stable issue gives:

- one place to watch active repo-health drift
- one place to discuss accepted findings
- one object the PM can route into work items or maintenance backlog

## Expected drift-monitor operating flow

The intended operating flow is:

1. run `scripts/drift/run_all.py`
2. inspect `latest_report.json` and `summary.md`
3. if needed, run a repo-wide drift-monitor audit using those artifacts as the first evidence surface
4. route findings to PM, repository maintenance, PRD, methodology/spec, coding, review, or human
5. if a finding is accepted but deferred, add it to `baseline.json` with rationale and an issue reference

The deterministic suite narrows the audit problem. It does not replace PM or human judgment.

## Known limits

The current deterministic layer does not yet cover:

- archived-versus-active canon lineage drift beyond broken references
- semantic contradiction between two docs that both still exist
- deeper architecture-boundary violations in import graphs or runtime behavior
- prose quality beyond narrow measurable drift indicators

Those gaps are intentional. The deterministic layer should stay specific, explainable, and low-noise.

## Extension rules

When adding a new deterministic scanner:

1. give it a dedicated implementation module under `agent_runtime/drift/`
2. give it a dedicated CLI entrypoint under `scripts/drift/`
3. define stable finding shapes and signatures
4. add focused unit tests and a repo-baseline test if appropriate
5. wire it into `drift_suite.py`
6. add its artifact path to `artifacts/drift/README.md`
7. update `docs/delivery/05_repo_drift_monitoring.md`
8. update workflow artifact upload if a new per-scanner JSON is produced

Good deterministic scanners should:

- operate on clearly defined repo surfaces
- emit evidence-rich findings
- avoid fuzzy heuristics that create noise
- degrade explicitly when required files are missing or malformed

## Suggested reading

Use this feature reference together with:

- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/repo_health_audit_checklist.md`
- `artifacts/drift/README.md`

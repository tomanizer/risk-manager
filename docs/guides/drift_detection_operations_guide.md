# Drift Detection Operations Guide

## Purpose

This guide explains how to operate the implemented drift-detection system in day-to-day repository governance.

Use it when you need to:

- run the suite manually
- interpret suite artifacts
- decide whether to baseline a finding
- understand the scheduled issue-upsert workflow
- extend the system safely

## Operator workflow

### 1. Run on current `main`

Always run drift detection against current `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
python scripts/drift/run_all.py --root . --artifact-dir artifacts/drift --output artifacts/drift/latest_report.json --summary-output artifacts/drift/summary.md
```

This avoids reporting drift against stale local guidance.

### 2. Read the summary first

Start with:

- `artifacts/drift/summary.md`

Use it to answer:

- did any scanner find raw drift at all
- are there any net-new findings after baseline filtering
- which scanner produced them

### 3. Use the aggregate JSON for precise routing

Then inspect:

- `artifacts/drift/latest_report.json`

That file is the machine-readable contract for:

- the workflow
- issue automation
- future scanner composition
- any higher-level drift-monitor prompt pass

### 4. Read the per-scanner artifact only when needed

Use a per-scanner JSON when:

- one scanner produced the net-new findings
- you need the scanner-specific stats
- you want the raw evidence before broader repo reading

## Interpreting findings

### Raw findings versus net-new findings

The deterministic system makes an important distinction:

- `total_findings`: everything currently present
- `new_findings`: findings not covered by the baseline
- `waived_findings`: findings still present but accepted in `baseline.json`

Operationally:

- use `new_findings` for alerting
- use `waived_findings` for known debt tracking
- use `total_findings` for overall burden awareness

### Severity still matters

Baseline filtering does not make a finding unimportant. It only changes whether the suite treats it as newly alertable drift.

A waived finding can still be severe. That is why the rationale and linked issue should stay explicit.

## Baselining policy

### When to baseline

Baseline a finding only when all of these are true:

- the finding is understood
- the finding has a clear owner
- the finding has a known remediation path
- repeated re-alerting would add little value before that remediation happens

### What to record

Every baseline entry should have:

- the exact scanner name
- the exact signature
- a short rationale

Strongly preferred:

- a linked issue number
- an expiry date if the waiver should be revisited

### Bad baseline patterns

Avoid:

- bulk-baselining a whole scanner
- vague rationales like `known` or `later`
- baselining a finding before anyone agrees it is real
- baselining active policy conflicts

## Scheduled workflow behavior

### What happens when there are net-new findings

The workflow:

1. runs the suite
2. renders `issue_body.md`
3. finds the stable repo-health issue using title plus hidden marker
4. creates the issue if it does not exist
5. updates the issue if it already exists

This means the repo should have one stable drift issue, not a growing pile of duplicate issues.

### What happens when drift returns to zero

When the suite reports zero net-new findings:

- the workflow closes the stable repo-health issue if it is open
- the issue body is updated to reflect the zero-findings state

This keeps the issue lifecycle aligned with the actual suite state.

### Why pagination matters

The issue lookup must paginate through repository issues rather than checking only the first page. Otherwise large repositories can fail to find the stable issue and create duplicates.

That behavior is now implemented in the workflow.

## How to triage scanner output

### Dependency hygiene findings

Usually route to:

- repository maintenance

Escalate beyond maintenance when:

- dependency drift reflects a real architecture decision
- packaging policy is no longer aligned with delivery canon

### Instruction-surface findings

Usually route to:

- repository maintenance

Escalate to PM or human when:

- the repeated instructions reflect a true governance conflict rather than stale restatement

### Reference-integrity findings

Route based on source:

- PM when work-item or canon navigation is breaking planning
- repository maintenance when the problem is an instruction-pack or generated-artifact path

### Registry-alignment findings

Usually route to:

- PM

Escalate when:

- the registry and implemented reality disagree on what is truly current

## How to add a new scanner safely

### Required design steps

Before implementing a new deterministic scanner:

1. define the exact repo surface being checked
2. define the stable finding shape
3. define the signature fields used by baseline matching
4. define who normally owns the resulting fixes
5. define what the scanner explicitly does not try to judge

### Required repo changes

A new scanner should usually require changes in all of these areas:

- implementation module in `agent_runtime/drift/`
- CLI entrypoint in `scripts/drift/`
- tests in `tests/unit/agent_runtime/`
- suite registration in `agent_runtime/drift/drift_suite.py`
- artifact listing in `artifacts/drift/README.md`
- workflow artifact upload if a per-scanner JSON is emitted
- delivery docs in `docs/delivery/05_repo_drift_monitoring.md`

### Noise control rule

If a proposed scanner cannot explain its findings with stable, inspectable evidence, it probably should not be deterministic.

Keep deterministic scanners:

- narrow
- explicit
- predictable
- low-noise

## How to debug drift-suite behavior

### If a scanner suddenly reports many findings

Check:

- whether a shared path moved
- whether a README inventory or role pair is now stale
- whether a baseline signature stopped matching because the finding shape changed
- whether the repo was run from stale local state

### If the suite reports findings but the issue did not update

Check:

- workflow permissions
- `actions/github-script` execution
- whether the issue marker changed
- whether issue lookup pagination still works
- whether the job failed before the upsert step

### If the suite reports no findings when you expected some

Check:

- whether the relevant finding is currently baselined
- whether the scanner was wired into `drift_suite.py`
- whether the target file surface is actually in the repo path being scanned
- whether a generated path is intentionally sanctioned

## Current implementation map

Core suite:

- `agent_runtime/drift/drift_suite.py`
- `scripts/drift/run_all.py`

Current scanners:

- `agent_runtime/drift/dependency_hygiene.py`
- `agent_runtime/drift/instruction_surfaces.py`
- `agent_runtime/drift/reference_integrity.py`
- `agent_runtime/drift/registry_alignment.py`

Issue rendering:

- `scripts/drift/render_issue_body.py`

Workflow:

- `.github/workflows/drift-monitor.yml`

Baseline:

- `artifacts/drift/baseline.json`

## Recommended human practice

The deterministic system works best when humans keep three habits:

1. keep baseline entries narrow and justified
2. treat net-new findings as governance signals, not as random cleanup
3. use the stable repo-health issue to track active drift until it is actually resolved

## Suggested reading

Read this guide together with:

- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/drift_detection_feature_reference.md`
- `docs/guides/repo_health_audit_checklist.md`

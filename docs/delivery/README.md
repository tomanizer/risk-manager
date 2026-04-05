# Delivery Pack

## Purpose

This folder captures delivery-management canon for the PM agent and adjacent repo-health controls.

These documents exist to make the delivery governance model more than a generic backlog process. The PM agent in this repository is expected to make strong readiness, dependency, slicing, and escalation judgments for an AI-mediated delivery loop, and the repo also uses a separate drift-monitoring control to audit whole-repository coherence over time.

## Initial contents

- `01_pm_operating_model.md`
- `02_readiness_and_dependency_framework.md`
- `03_slice_sizing_and_pr_strategy.md`
- `04_review_triage_and_escalation.md`
- `05_repo_drift_monitoring.md`
- `exemplars/PM-X1-ready-vs-blocked-example.md`
- `exemplars/PM-X2-implementation-brief-example.md`

## Rule

PM work should use this pack alongside `work_items/READY_CRITERIA.md`, the linked work item, the linked PRD, and the linked ADRs.

Drift-monitor work should use `05_repo_drift_monitoring.md` together with `docs/guides/repo_health_audit_checklist.md`.

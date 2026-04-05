# Repo Health Audit Prompt

Audit this repository for repo-wide drift.

Read:

- `AGENTS.md`
- `docs/delivery/05_repo_drift_monitoring.md`
- `docs/guides/repo_health_audit_checklist.md`
- `docs/registry/current_state_registry.yaml`
- deterministic precheck output if present under `artifacts/drift/`
- relevant canon, PRD, ADR, prompt, work-item, source, and test artifacts needed to assess coherence

Audit for:

- contradiction across canon and prompts
- duplicated or diverging source-of-truth content
- stale or misleading registry, README, or catalog state
- architecture-boundary erosion
- tooling or dependency drift such as missing packaging, mismatched CI checks, or declared dependencies that are not yet used
- maturity/status drift between implemented reality and declared registry or roadmap state
- instruction sprawl across agent and tool surfaces
- sprawling, repetitive, or weakly governed documentation

Rules:

- run deterministic drift scanners first when they exist, starting with:
  - `python scripts/drift/check_references.py --root . --output artifacts/drift/reference_integrity.json`
  - `python scripts/drift/check_registry_alignment.py --root . --output artifacts/drift/registry_alignment.json`
- cite evidence for each material finding
- distinguish sanctioned duplication from unhealthy duplication
- classify each material finding as canon, implementation, tooling, operational-instruction, or maturity/status drift
- route each finding to PM, PRD, methodology/spec, coding, review, repository maintenance, or human
- do not rewrite artifacts unless explicitly asked
- do not give merge approval

Return:

1. overall repo health status: `HEALTHY`, `WATCH`, or `DRIFTING`
2. findings by severity (critical, major, minor)
3. evidence for each material finding
4. drift class for each material finding
5. why each finding matters
6. owner and routing recommendation for each material finding
7. whether any duplication is sanctioned and acceptable
8. smallest next action for each critical or major finding

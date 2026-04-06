# Repo Health Audit Prompt

This file is superseded. The canonical sources are:

- Standing instruction: `prompts/agents/drift_monitor_agent_instruction.md`
- Invocation template: `prompts/agents/invocation_templates/drift_monitor_invocation.md`

Run deterministic scanners first: `python scripts/drift/run_all.py --root . --artifact-dir artifacts/drift --output artifacts/drift/latest_report.json --summary-output artifacts/drift/summary.md`

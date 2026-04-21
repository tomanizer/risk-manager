# risk-manager

AI-enabled market risk platform for daily investigation, FRTB / PLA controls, limits and approvals, operational integrity, desk status, governance reporting, and controlled change assessment.

## Repository purpose

This repository is the governed source of truth for:
- the target operating model (TOM)
- architecture and design principles
- architectural decision records (ADRs)
- phased implementation roadmap
- PRD templates and exemplars
- work items and prompts for AI-mediated delivery
- source code, tests, and replay fixtures

## Core architecture

The platform is organized into:
1. **Capability Modules**: deterministic logic, business rules, canonical business state, audit trails
2. **Specialist Walkers**: typed interpretation over module outputs
3. **Process Orchestrators**: workflow state, workflow execution, routing, gates, challenge, and handoff

## Design doctrine

- deterministic core, agentic edge
- evidence-first and replayable
- typed interfaces only
- KISS and YAGNI
- no hidden policy in UI
- no raw calculations in orchestrators
- no silent bypass of trust or challenge gates

## Local setup

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 2. Configure API keys
cp .env.example .env
# Edit .env and fill in the keys for the providers you use (all optional).

# 3. Install the repo-tracked pre-push hook (once per clone)
pre-commit install --hook-type pre-push
```

The pre-push hook runs through the repo-local `.venv`, so pushes from
non-activated shells and GUI clients still use the project dev
environment. It auto-applies Ruff fixes and formatting locally. If it
rewrites files, stage the changes and push again.

See `agent_runtime/config/README.md` for the full environment variable
reference, and `docs/guides/agent_framework.md` for tool-specific setup
(Cursor, Claude Code, Codex, Copilot).

## Initial canon

See `docs/` for the current approved architecture canon.

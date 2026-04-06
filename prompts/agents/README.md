# Agent Instruction Documents

## Purpose

This folder holds the canonical operating instructions for the repository's delivery agents and repo-health control agents.

These instructions are the single source of truth for each agent's responsibilities, reading order, operating rules, stop conditions, and forbidden behavior. Tool-specific surfaces (`.github/agents/`, `CLAUDE.md`, `GEMINI.md`) should be thin pointers that reference these files.

## Agent index

| Agent | Instruction File | Copilot Agent | Invocation Template |
|-------|-----------------|---------------|-------------------|
| PM / Coordination | `pm_agent_instruction.md` | `.github/agents/pm.agent.md` | `invocation_templates/pm_invocation.md` |
| PRD / Spec Author | `prd_spec_agent_instruction.md` | `.github/agents/prd-spec.agent.md` | `invocation_templates/prd_spec_invocation.md` |
| Issue Planner | `issue_planner_instruction.md` | `.github/agents/issue-planner.agent.md` | `invocation_templates/issue_planner_invocation.md` |
| Coding | `coding_agent_instruction.md` | `.github/agents/coding.agent.md` | `invocation_templates/coding_invocation.md` |
| Review | `review_agent_instruction.md` | `.github/agents/review.agent.md` | `invocation_templates/review_invocation.md` |
| Drift Monitor | `drift_monitor_agent_instruction.md` | `.github/agents/drift-monitor.agent.md` | `invocation_templates/drift_monitor_invocation.md` |

The Risk Methodology Spec Agent (`risk_methodology_spec_agent_instruction.md`) is retained for backward compatibility. New methodology-aware specification work should use the PRD / Spec Author agent, which incorporates methodology judgment.

## Structure

```
prompts/agents/
├── README.md                              (this file)
├── pm_agent_instruction.md                (standing instruction)
├── prd_spec_agent_instruction.md          (standing instruction)
├── issue_planner_instruction.md           (standing instruction)
├── coding_agent_instruction.md            (standing instruction)
├── review_agent_instruction.md            (standing instruction)
├── drift_monitor_agent_instruction.md     (standing instruction)
├── risk_methodology_spec_agent_instruction.md  (legacy, folded into prd_spec)
└── invocation_templates/
    ├── README.md
    ├── pm_invocation.md                   (per-task prompt template)
    ├── prd_spec_invocation.md
    ├── issue_planner_invocation.md
    ├── coding_invocation.md
    ├── review_invocation.md
    └── drift_monitor_invocation.md
```

## Precedence rule

If a local artifact conflicts with a broader artifact, prefer the more local implementation artifact and record the ambiguity explicitly:

1. work item
2. linked PRD
3. linked ADR
4. local module or workflow documentation
5. repo-wide canon

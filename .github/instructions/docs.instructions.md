---
applyTo: "docs/**/*.md,prompts/**/*.md,work_items/**/*.md,README.md,AGENTS.md"
---

# Documentation and PRD instructions

These files are part of the governed architecture canon and AI delivery system.

## Rules
- Keep docs precise, implementation-facing, and low-fluff.
- Preserve the separation between TOM, ADRs, PRDs, prompts, and work items.
- PRDs must be bounded implementation contracts, not strategy essays.
- Always include explicit in-scope and out-of-scope sections when editing PRDs.
- Preserve acceptance criteria, degraded-case handling, evidence/logging requirements, and issue decomposition guidance.
- Do not quietly reopen architecture decisions that are already settled in the canon.

## Review checks
- Does the document match the correct template or artifact type?
- Does it stay inside the component boundary?
- Does it preserve architecture and ownership terminology consistently?
- Does it avoid introducing hidden assumptions?

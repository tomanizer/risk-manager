---
applyTo: "src/**/*.ts,src/**/*.tsx,src/**/*.js,src/**/*.jsx,src/**/*.css"
---

# UI and presentation instructions

UI code in this repository must remain a presentation and workflow-consumption layer.

## Rules
- Do not recompute canonical business logic in the UI.
- Do not suppress trust, caveat, challenge, or unresolved-state indicators for neatness.
- Consume typed backend outputs only.
- Preserve evidence drill-through and explicit state handling.
- Use approved design tokens and branding rules where defined.
- Keep interaction logic separate from orchestration and calculation logic.

## Review checks
- Are blocked, degraded, and unresolved states clearly visible?
- Is caveat placement close to conclusions?
- Has any backend contract been invented ad hoc in the UI?
- Does the UI avoid hidden policy or analytical logic?

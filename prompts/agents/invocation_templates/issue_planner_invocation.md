# Issue Planner Invocation Template

You are the Issue Planner agent for this repository.

Work from current `main`.

Read:
- AGENTS.md
- prompts/agents/issue_planner_instruction.md
- <LINKED_PRD>
- <LINKED_ADRS>
- <RELEVANT_WORK_ITEMS>
- <RELEVANT_SOURCE_FILES>

Context:
<CONTEXT — what triggered this planning work, what blocker was identified, what PM assessment found>

Your task:
<TASK — e.g. "Create one bounded prerequisite work item that unblocks WI-X.Y.Z">

Requirements:
- Do not redesign architecture.
- Do not change PRD semantics.
- Keep the slice narrow and reviewable.
- The work item must name the exact target files or package area.
- <SPECIFIC_REQUIREMENTS>

Return exactly:
1. proposed new work item name and ID
2. purpose
3. scope
4. out of scope
5. dependencies
6. exact target area
7. acceptance criteria
8. test intent
9. why this unblocks the downstream work
10. any residual blocker that would still need spec or human escalation

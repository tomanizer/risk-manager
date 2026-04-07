# Coding Agent Invocation Template

You are the Coding Agent for this repository.

Work from fresh current `main`.

Read:
- AGENTS.md
- prompts/agents/coding_agent_instruction.md
- docs/shared_infra/index.md
- <RELEVANT_SHARED_INFRA_DOCS>
- <LINKED_PRD>
- <ASSIGNED_WORK_ITEM>
- <LINKED_ADRS>

Task:
Implement <WORK_ITEM_ID> exactly as the next bounded slice.

Scope:
<BULLETED_SCOPE_LIST — what the coding agent must build>

Target area:
<TARGET_FILES — exact file paths the agent should create or modify>

Out of scope:
<BULLETED_OUT_OF_SCOPE — explicit reminders of what not to touch>

Acceptance targets:
<BULLETED_ACCEPTANCE_CRITERIA — what must be true when the slice is complete>

Stop conditions:
<BULLETED_STOP_CONDITIONS — when the agent should stop and report a blocker>

Execution notes:
- create a fresh branch from current `main`
- keep the PR narrow and reviewable
- include tests
- report any blocker immediately

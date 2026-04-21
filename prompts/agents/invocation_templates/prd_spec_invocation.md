# PRD / Spec Author Invocation Template

You are the PRD / Spec Author agent for this repository.

Work from the governed execution checkout for this task.

Execution mode:
- If this handoff is run through agent_runtime, the runtime-managed worktree for this run is authoritative. Do not switch to `main`. Do not create another worktree. Do not create another branch.
- If this handoff is run manually outside `agent_runtime`, refresh the control checkout on current `main` and create a fresh branch from current `main` before authoring the PRD/spec update.

Read:
- AGENTS.md
- prompts/agents/prd_spec_agent_instruction.md
- docs/shared_infra/index.md
- <RELEVANT_SHARED_INFRA_DOCS>
- <LINKED_ADRS>
- <EXISTING_PRD_IF_UPDATING>
- <RELEVANT_WORK_ITEMS>
- <RELEVANT_SOURCE_FILES>

Context:
<CONTEXT — what triggered this PRD/spec work, what gap exists, what has changed>

Task:
<TASK — e.g. "Write PRD for X capability" or "Update PRD-1.1 to clarify error semantics for as-of-date retrieval">

Required outcomes:
<NUMBERED_LIST — specific clarifications, contract decisions, or sections the PRD must address>

Important constraints:
- Do not rewrite unrelated parts of the PRD.
- Do not push ambiguity back to coding.
- Keep the change narrow and reviewable.
- Preserve consistency with existing ADRs.
- <ADDITIONAL_CONSTRAINTS>

Focus areas:
<FOCUS_AREAS — specific PRD sections, contracts, or status-model wording to address>

Expected result:
<EXPECTED_RESULT — what the finished PRD/spec enables downstream>

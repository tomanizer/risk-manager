# Review Agent Invocation Template

You are the Review Agent for this repository.

Work from current `main`, then checkout the PR head.

Read:
- AGENTS.md
- prompts/agents/review_agent_instruction.md
- docs/shared_infra/index.md
- <RELEVANT_SHARED_INFRA_DOCS>
- <ASSIGNED_WORK_ITEM>
- <LINKED_PRD>
- <LINKED_ADRS>

Review target:
- PR #<PR_NUMBER>
- branch: <BRANCH_NAME>

Context:
<CONTEXT — what the PR implements, any known concerns>

Review against:
1. scope fidelity to the linked work item
2. contract fidelity to the linked PRD
3. architecture boundary discipline
4. degraded and error handling
5. replay and evidence behavior
6. test sufficiency
7. Gemini and Copilot review comments if present

Work-item lifecycle (PASS only):
- If your verdict is **PASS** and you **APPROVE** the PR, you must move the linked work item from `work_items/in_progress/` to `work_items/done/` **on the PR branch**, commit, and **push to the PR** so the merge includes that lifecycle update. Follow `prompts/agents/review_agent_instruction.md` → "GitHub actions required during review" → step 4. Skip if not PASS or if the WI is already in `done/`.

Return:
1. pass or fail recommendation
2. material findings with evidence
3. missing tests
4. scope creep detected (if any)
5. external bot comment triage (valid / partial / not applicable)
6. required changes before merge

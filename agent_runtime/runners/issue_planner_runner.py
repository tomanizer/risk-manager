"""Issue Planner runner — dispatches the Issue Planner agent."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult


@dataclass(frozen=True)
class IssuePlannerRunnerInput:
    work_item_id: str
    split_reason: str
    work_item_path: str
    linked_prd: str | None = None


def build_issue_planner_prompt(input_data: IssuePlannerRunnerInput) -> str:
    prompt = (
        "Act only as the Issue Planner agent.\n"
        f"Work from current `main`.\n"
        f"Read:\n"
        f"- AGENTS.md\n"
        f"- prompts/agents/issue_planner_instruction.md\n"
    )
    if input_data.linked_prd:
        prompt += f"- {input_data.linked_prd}\n"
    prompt += (
        f"- {input_data.work_item_path}\n"
        f"\n"
        f"Context:\n"
        f"A PM assessment for {input_data.work_item_id} returned SPLIT_REQUIRED.\n"
        f"Reason: {input_data.split_reason}\n"
        f"\n"
        f"Your task:\n"
        f"Decompose {input_data.work_item_id} into bounded, sequenced work items that can each be\n"
        f"implemented in a single narrow PR. Do not redesign architecture. Do not change PRD semantics.\n"
        f"Keep each slice narrow and reviewable. Name exact target files or package areas for each slice.\n"
        f"\n"
        f"Return exactly:\n"
        f"1. proposed new work item names and IDs\n"
        f"2. purpose of each\n"
        f"3. scope of each\n"
        f"4. out of scope for each\n"
        f"5. dependencies between the proposed slices\n"
        f"6. exact target area for each\n"
        f"7. acceptance criteria for each\n"
        f"8. test intent for each\n"
        f"9. why this decomposition unblocks the original work item\n"
        f"10. any residual blocker that would need spec or human escalation\n"
    )
    return prompt


def dispatch_issue_planner_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.ISSUE_PLANNER:
        raise RuntimeError("Issue Planner dispatch received a non-issue-planner runner execution")
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared issue-planning handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

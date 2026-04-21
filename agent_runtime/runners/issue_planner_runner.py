"""Issue Planner runner — dispatches the Issue Planner agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .prompt_loader import load_system_prompt


@dataclass(frozen=True)
class IssuePlannerRunnerInput:
    work_item_id: str
    split_reason: str
    work_item_path: str
    linked_prd: str | None = None
    source_prd_path: str | None = None
    missing_work_item_ids: tuple[str, ...] = ()


def build_issue_planner_prompt(input_data: IssuePlannerRunnerInput) -> str:
    prompt = (
        "Act only as the Issue Planner agent.\n"
        "If dispatched by agent_runtime, treat the allocated worktree as authoritative and do not switch to `main`, "
        "create another worktree, or create another branch.\n"
        "If running manually outside agent_runtime, refresh current `main` and create a fresh branch from current `main` before editing work items.\n"
        "Read:\n"
        "- AGENTS.md\n"
        "- prompts/agents/issue_planner_instruction.md\n"
    )
    if input_data.source_prd_path:
        prompt += f"- {input_data.source_prd_path}\n"
    elif input_data.linked_prd:
        prompt += f"- {input_data.linked_prd}\n"
    prompt += f"- {input_data.work_item_path}\n\nContext:\n"
    if input_data.source_prd_path and input_data.missing_work_item_ids:
        missing_ids = ", ".join(input_data.missing_work_item_ids)
        prompt += (
            f"The linked implementation-ready PRD names follow-on work items that are not yet materialized in the live backlog.\n"
            f"PRD: {input_data.source_prd_path}\n"
            f"Missing work items: {missing_ids}\n"
            f"Trigger: {input_data.split_reason}\n"
            f"\n"
            f"Your task:\n"
            f"Materialize the missing follow-on work items for {input_data.source_prd_path} into bounded,\n"
            f"sequenced backlog slices that can each be implemented in a single narrow PR. Do not redesign\n"
            f"architecture. Do not change PRD semantics. If the PRD already names specific WI IDs, preserve them.\n"
            f"Do not decompose {input_data.work_item_id} itself again unless the PRD text is insufficient.\n"
            f"Name exact target files or package areas for each slice.\n"
            f"\n"
        )
    else:
        prompt += (
            f"A PM assessment for {input_data.work_item_id} returned SPLIT_REQUIRED.\n"
            f"Reason: {input_data.split_reason}\n"
            f"\n"
            f"Your task:\n"
            f"Decompose {input_data.work_item_id} into bounded, sequenced work items that can each be\n"
            f"implemented in a single narrow PR. Do not redesign architecture. Do not change PRD semantics.\n"
            f"Keep each slice narrow and reviewable. Name exact target files or package areas for each slice.\n"
            f"\n"
        )
    prompt += (
        "Return exactly:\n"
        "1. proposed new work item names and IDs\n"
        "2. purpose of each\n"
        "3. scope of each\n"
        "4. out of scope for each\n"
        "5. dependencies between the proposed slices\n"
        "6. exact target area for each\n"
        "7. acceptance criteria for each\n"
        "8. test intent for each\n"
        "9. why this decomposition unblocks the original work item\n"
        "10. any residual blocker that would need spec or human escalation\n"
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


class IssuePlannerRunner:
    """RunnerProtocol implementation for the Issue Planner role."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    @property
    def runner_name(self) -> RunnerName:
        return RunnerName.ISSUE_PLANNER

    def get_system_prompt(self) -> str:
        return load_system_prompt(RunnerName.ISSUE_PLANNER, self._repo_root)

    def prepare(self, execution: RunnerExecution) -> RunnerResult:
        return dispatch_issue_planner_execution(execution)

    async def execute(self, execution: RunnerExecution) -> RunnerResult:
        return dispatch_issue_planner_execution(execution)

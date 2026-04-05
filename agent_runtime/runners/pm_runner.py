"""PM runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult


@dataclass(frozen=True)
class PMRunnerInput:
    work_item_id: str
    work_item_path: str
    linked_prd: str | None = None


def build_pm_prompt(input_data: PMRunnerInput) -> str:
    prompt = (
        "Act only as the PM agent.\n"
        f"Assess readiness for work item {input_data.work_item_id} "
        f"using {input_data.work_item_path} as the local target artifact."
    )
    if input_data.linked_prd is not None:
        prompt += f"\nLinked PRD: {input_data.linked_prd}."
    return prompt


def dispatch_pm_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.PM:
        raise RuntimeError("PM dispatch received a non-PM runner execution")
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared PM readiness handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

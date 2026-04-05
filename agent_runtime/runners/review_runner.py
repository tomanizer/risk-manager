"""Review runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult


@dataclass(frozen=True)
class ReviewRunnerInput:
    work_item_id: str
    pr_number: int
    pr_url: str | None = None


def build_review_prompt(input_data: ReviewRunnerInput) -> str:
    prompt = f"Act only as the review agent.\nReview PR #{input_data.pr_number} for {input_data.work_item_id}."
    if input_data.pr_url is not None:
        prompt += f"\nPR URL: {input_data.pr_url}"
    return prompt


def dispatch_review_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.REVIEW:
        raise RuntimeError("Review dispatch received a non-review runner execution")
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared review handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

"""Review runner — PR triage against governed criteria."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .prompt_loader import load_system_prompt
from .review_backend import (
    REVIEW_BACKEND_CODEX_EXEC,
    REVIEW_BACKEND_PREPARED,
    dispatch_codex_review_execution,
    dispatch_prepared_review_execution,
    get_review_backend_name,
)


@dataclass(frozen=True)
class ReviewRunnerInput:
    work_item_id: str
    pr_number: int
    pr_url: str | None = None
    base_ref: str | None = None


def build_review_prompt(input_data: ReviewRunnerInput) -> str:
    prompt = f"Act only as the review agent.\nReview PR #{input_data.pr_number} for {input_data.work_item_id}."
    if input_data.pr_url is not None:
        prompt += f"\nPR URL: {input_data.pr_url}"
    if input_data.base_ref is not None:
        prompt += f"\nBase ref: {input_data.base_ref}"
    return prompt


class ReviewRunner:
    """RunnerProtocol implementation for the review role."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    @property
    def runner_name(self) -> RunnerName:
        return RunnerName.REVIEW

    def get_system_prompt(self) -> str:
        return load_system_prompt(RunnerName.REVIEW, self._repo_root)

    def prepare(self, execution: RunnerExecution) -> RunnerResult:
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

    async def execute(self, execution: RunnerExecution) -> RunnerResult:
        return self.prepare(execution)


def dispatch_review_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.REVIEW:
        raise RuntimeError("Review dispatch received a non-review runner execution")
    backend_name = get_review_backend_name()
    if backend_name == REVIEW_BACKEND_PREPARED:
        return dispatch_prepared_review_execution(execution)
    if backend_name == REVIEW_BACKEND_CODEX_EXEC:
        return dispatch_codex_review_execution(execution)
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.FAILED,
        summary=f"Unsupported review backend configured: {backend_name}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

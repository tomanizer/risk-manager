"""Review runner — PR triage against governed criteria."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_runtime.config import get_settings
from ._outcome_parsing import get_output_schema
from .contracts import BackendType, RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .prompt_loader import load_system_prompt
from .review_backend import ALLOWED_REVIEW_DECISIONS, dispatch_codex_review_execution, dispatch_prepared_review_execution

_REPO_ROOT = Path(__file__).parent.parent.parent


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

    cfg = get_settings().agent_runtime
    backend = cfg.get_role_backend("review")

    if backend is BackendType.PREPARED:
        return dispatch_prepared_review_execution(execution)

    if backend is BackendType.CODEX_EXEC:
        return dispatch_codex_review_execution(
            execution,
            codex_bin=cfg.review_codex_bin,
            model=cfg.review_codex_model or None,
        )

    if backend is BackendType.OPENAI_API:
        from .openai_backend import dispatch_openai_reasoning

        return dispatch_openai_reasoning(
            execution,
            repo_root=_REPO_ROOT,
            model=cfg.get_role_model("review", backend),
            allowed_decisions=ALLOWED_REVIEW_DECISIONS,
            output_schema=get_output_schema(RunnerName.REVIEW),
        )

    if backend is BackendType.ANTHROPIC_API:
        from .anthropic_backend import dispatch_anthropic_reasoning

        return dispatch_anthropic_reasoning(
            execution,
            repo_root=_REPO_ROOT,
            model=cfg.get_role_model("review", backend),
            allowed_decisions=ALLOWED_REVIEW_DECISIONS,
            output_schema=get_output_schema(RunnerName.REVIEW),
        )

    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.FAILED,
        summary=f"Unsupported review backend configured: {backend}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

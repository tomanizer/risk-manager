"""Coding runner — bounded implementation and CI repair."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from agent_runtime.config import BackendType, get_settings

from .coding_backend import ALLOWED_CODING_DECISIONS, dispatch_codex_coding_execution, dispatch_prepared_coding_execution
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .prompt_loader import load_system_prompt

_REPO_ROOT = Path(__file__).parent.parent.parent


@dataclass(frozen=True)
class CodingRunnerInput:
    work_item_id: str
    task_summary: str
    pr_number: int | None = None
    pr_url: str | None = None
    base_ref: str | None = None
    drift_summary: str | None = None


def build_coding_prompt(input_data: CodingRunnerInput) -> str:
    prompt = f"Act only as the coding agent.\nImplement or repair {input_data.work_item_id}.\nTask: {input_data.task_summary}"
    if input_data.pr_number is not None:
        prompt += f"\nPR: #{input_data.pr_number}"
    if input_data.pr_url is not None:
        prompt += f" ({input_data.pr_url})"
    if input_data.base_ref is not None:
        prompt += f"\nBase ref: {input_data.base_ref}"
    if input_data.drift_summary is not None:
        prompt += f"\n\n## Current repo drift state\n\n{input_data.drift_summary}"
    return prompt


class CodingRunner:
    """RunnerProtocol implementation for the coding role."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    @property
    def runner_name(self) -> RunnerName:
        return RunnerName.CODING

    def get_system_prompt(self) -> str:
        return load_system_prompt(RunnerName.CODING, self._repo_root)

    def prepare(self, execution: RunnerExecution) -> RunnerResult:
        if execution.runner_name is not RunnerName.CODING:
            raise RuntimeError("Coding dispatch received a non-coding runner execution")
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.PREPARED,
            summary=f"Prepared coding handoff for {execution.work_item_id}.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    async def execute(self, execution: RunnerExecution) -> RunnerResult:
        return self.prepare(execution)


def dispatch_coding_execution(execution: RunnerExecution) -> RunnerResult:
    """Dispatch the coding execution through the configured backend."""
    if execution.runner_name is not RunnerName.CODING:
        raise RuntimeError("Coding dispatch received a non-coding runner execution")

    try:
        cfg = get_settings().agent_runtime
    except ValidationError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Coding runner config is invalid: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    backend = cfg.get_role_backend("coding")

    if backend is BackendType.PREPARED:
        return dispatch_prepared_coding_execution(execution)

    if backend is BackendType.CODEX_EXEC:
        return dispatch_codex_coding_execution(
            execution,
            codex_bin=cfg.coding_codex_bin,
            model=cfg.coding_codex_model,
        )

    # OPENAI_API and ANTHROPIC_API tool-loop coding backends are implemented in WI-C.
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.FAILED,
        summary=f"Unsupported coding backend configured: {backend.value}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )


# Expose for use by WI-C tool-loop backends.
__all__ = [
    "ALLOWED_CODING_DECISIONS",
    "CodingRunner",
    "CodingRunnerInput",
    "build_coding_prompt",
    "dispatch_coding_execution",
]

"""PM runner — readiness assessment and implementation brief."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .pm_backend import (
    PM_BACKEND_CODEX_EXEC,
    PM_BACKEND_PREPARED,
    dispatch_codex_pm_execution,
    dispatch_prepared_pm_execution,
    get_pm_backend_name,
)
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .prompt_loader import load_system_prompt


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


class PMRunner:
    """RunnerProtocol implementation for the PM role."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    @property
    def runner_name(self) -> RunnerName:
        return RunnerName.PM

    def get_system_prompt(self) -> str:
        return load_system_prompt(RunnerName.PM, self._repo_root)

    def prepare(self, execution: RunnerExecution) -> RunnerResult:
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

    async def execute(self, execution: RunnerExecution) -> RunnerResult:
        return self.prepare(execution)


def dispatch_pm_execution(execution: RunnerExecution) -> RunnerResult:
    """Backward-compatible dispatch entry point."""
    if execution.runner_name is not RunnerName.PM:
        raise RuntimeError("PM dispatch received a non-PM runner execution")
    backend_name = get_pm_backend_name()
    if backend_name == PM_BACKEND_PREPARED:
        return dispatch_prepared_pm_execution(execution)
    if backend_name == PM_BACKEND_CODEX_EXEC:
        return dispatch_codex_pm_execution(execution)
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.FAILED,
        summary=f"Unsupported PM backend configured: {backend_name}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

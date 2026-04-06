"""PM runner — readiness assessment and implementation brief."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from agent_runtime.config import BackendType, get_settings

from ._outcome_parsing import get_output_schema
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .pm_backend import ALLOWED_PM_DECISIONS, dispatch_codex_pm_execution, dispatch_prepared_pm_execution
from .prompt_loader import load_system_prompt

_REPO_ROOT = Path(__file__).parent.parent.parent


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
    """Dispatch the PM execution through the configured backend."""
    if execution.runner_name is not RunnerName.PM:
        raise RuntimeError("PM dispatch received a non-PM runner execution")

    try:
        cfg = get_settings().agent_runtime
    except ValidationError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"PM runner config is invalid: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    backend = cfg.get_role_backend("pm")

    if backend is BackendType.PREPARED:
        return dispatch_prepared_pm_execution(execution)

    if backend is BackendType.CODEX_EXEC:
        return dispatch_codex_pm_execution(
            execution,
            codex_bin=cfg.pm_codex_bin,
            model=cfg.pm_codex_model,
        )

    if backend is BackendType.OPENAI_API:
        from .openai_backend import dispatch_openai_reasoning

        repo_root_str = execution.metadata.get("repo_root")
        repo_root = Path(repo_root_str) if repo_root_str else _REPO_ROOT
        return dispatch_openai_reasoning(
            execution,
            repo_root=repo_root,
            model=cfg.pm_openai_model,
            allowed_decisions=ALLOWED_PM_DECISIONS,
            output_schema=get_output_schema(RunnerName.PM),
        )

    if backend is BackendType.ANTHROPIC_API:
        from .anthropic_backend import dispatch_anthropic_reasoning

        repo_root_str = execution.metadata.get("repo_root")
        repo_root = Path(repo_root_str) if repo_root_str else _REPO_ROOT
        return dispatch_anthropic_reasoning(
            execution,
            repo_root=repo_root,
            model=cfg.pm_anthropic_model,
            allowed_decisions=ALLOWED_PM_DECISIONS,
            output_schema=get_output_schema(RunnerName.PM),
        )

    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.FAILED,
        summary=f"Unsupported PM backend configured: {backend.value}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

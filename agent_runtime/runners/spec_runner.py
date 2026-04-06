"""Spec runner — methodology and blocker resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_runtime.config.settings import get_settings

from ._outcome_parsing import get_output_schema
from .contracts import BackendType, RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from .prompt_loader import load_system_prompt
from .spec_backend import ALLOWED_SPEC_DECISIONS, dispatch_codex_spec_execution, dispatch_prepared_spec_execution

_REPO_ROOT = Path(__file__).parent.parent.parent


@dataclass(frozen=True)
class SpecRunnerInput:
    work_item_id: str
    blocked_reason: str
    work_item_path: str
    linked_prd: str | None = None


def build_spec_prompt(input_data: SpecRunnerInput) -> str:
    return (
        "Act only as the spec-resolution agent.\n"
        f"Resolve the blocker for {input_data.work_item_id}.\n"
        f"Work item: {input_data.work_item_path}\n"
        f"Blocked reason: {input_data.blocked_reason}"
    )


class SpecRunner:
    """RunnerProtocol implementation for the spec/methodology role."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    @property
    def runner_name(self) -> RunnerName:
        return RunnerName.SPEC

    def get_system_prompt(self) -> str:
        return load_system_prompt(RunnerName.SPEC, self._repo_root)

    def prepare(self, execution: RunnerExecution) -> RunnerResult:
        if execution.runner_name is not RunnerName.SPEC:
            raise RuntimeError("Spec dispatch received a non-spec runner execution")
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.PREPARED,
            summary=f"Prepared spec-resolution handoff for {execution.work_item_id}.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    async def execute(self, execution: RunnerExecution) -> RunnerResult:
        return self.prepare(execution)


def dispatch_spec_execution(execution: RunnerExecution) -> RunnerResult:
    """Dispatch through the configured spec backend."""
    if execution.runner_name is not RunnerName.SPEC:
        raise RuntimeError("Spec dispatch received a non-spec runner execution")
    cfg = get_settings().agent_runtime
    backend = cfg.get_role_backend("spec")
    if backend == BackendType.PREPARED:
        return dispatch_prepared_spec_execution(execution)
    if backend == BackendType.CODEX_EXEC:
        return dispatch_codex_spec_execution(
            execution,
            codex_bin=cfg.get_role_codex_bin("spec"),
            model=cfg.get_role_model("spec", backend),
        )
    if backend is BackendType.OPENAI_API:
        from .openai_backend import dispatch_openai_reasoning

        return dispatch_openai_reasoning(
            execution,
            repo_root=_REPO_ROOT,
            model=cfg.get_role_model("spec", backend),
            allowed_decisions=ALLOWED_SPEC_DECISIONS,
            output_schema=get_output_schema(RunnerName.SPEC),
        )
    if backend is BackendType.ANTHROPIC_API:
        from .anthropic_backend import dispatch_anthropic_reasoning

        return dispatch_anthropic_reasoning(
            execution,
            repo_root=_REPO_ROOT,
            model=cfg.get_role_model("spec", backend),
            allowed_decisions=ALLOWED_SPEC_DECISIONS,
            output_schema=get_output_schema(RunnerName.SPEC),
        )
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.FAILED,
        summary=f"Unsupported spec backend configured: {backend.value}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )

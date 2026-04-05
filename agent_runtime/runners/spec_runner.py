"""Spec runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult


@dataclass(frozen=True)
class SpecRunnerInput:
    work_item_id: str
    blocked_reason: str
    work_item_path: str


def build_spec_prompt(input_data: SpecRunnerInput) -> str:
    return (
        "Act only as the spec-resolution agent.\n"
        f"Resolve the blocker for {input_data.work_item_id}.\n"
        f"Work item: {input_data.work_item_path}\n"
        f"Blocked reason: {input_data.blocked_reason}"
    )


def dispatch_spec_execution(execution: RunnerExecution) -> RunnerResult:
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

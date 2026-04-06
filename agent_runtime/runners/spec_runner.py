"""Spec runner — dispatches the PRD / Spec Author agent."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult


@dataclass(frozen=True)
class SpecRunnerInput:
    work_item_id: str
    blocked_reason: str
    work_item_path: str
    linked_prd: str | None = None


def build_spec_prompt(input_data: SpecRunnerInput) -> str:
    prompt = (
        "Act only as the PRD / Spec Author agent.\n"
        f"Work from current `main`.\n"
        f"Read:\n"
        f"- AGENTS.md\n"
        f"- prompts/agents/prd_spec_agent_instruction.md\n"
    )
    if input_data.linked_prd:
        prompt += f"- {input_data.linked_prd}\n"
    prompt += (
        f"\n"
        f"Context:\n"
        f"A PM assessment for {input_data.work_item_id} returned SPEC_REQUIRED.\n"
        f"Reason: {input_data.blocked_reason}\n"
        f"\n"
        f"Work item: {input_data.work_item_path}\n"
        f"\n"
        f"Task:\n"
        f"Resolve the specification gap that is blocking {input_data.work_item_id}.\n"
        f"Produce the minimal PRD or spec update needed to make the work item coding-ready.\n"
        f"Do not push ambiguity back to coding.\n"
        f"Keep the change narrow and reviewable.\n"
    )
    return prompt


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

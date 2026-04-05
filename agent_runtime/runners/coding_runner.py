"""Coding runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodingRunnerInput:
    work_item_id: str
    task_summary: str
    pr_number: int | None = None
    pr_url: str | None = None


def build_coding_prompt(input_data: CodingRunnerInput) -> str:
    prompt = f"Act only as the coding agent.\nImplement or repair {input_data.work_item_id}.\nTask: {input_data.task_summary}"
    if input_data.pr_number is not None:
        prompt += f"\nPR: #{input_data.pr_number}"
    if input_data.pr_url is not None:
        prompt += f" ({input_data.pr_url})"
    return prompt

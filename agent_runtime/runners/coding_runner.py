"""Coding runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodingRunnerInput:
    work_item_id: str
    implementation_brief: str


def build_coding_prompt(input_data: CodingRunnerInput) -> str:
    return f"Act only as the coding agent.\nImplement {input_data.work_item_id}.\nBrief: {input_data.implementation_brief}"

"""Coding runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodingRunnerInput:
    work_item_id: str
    implementation_brief: str


def build_coding_prompt(input_data: CodingRunnerInput) -> str:
    return (
        "Act only as the coding agent.\n"
        f"Implement {input_data.work_item_id}.\n"
        f"Brief: {input_data.implementation_brief}"
    )

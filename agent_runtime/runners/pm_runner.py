"""PM runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PMRunnerInput:
    work_item_id: str
    work_item_path: str


def build_pm_prompt(input_data: PMRunnerInput) -> str:
    return (
        "Act only as the PM agent.\n"
        f"Assess readiness for work item {input_data.work_item_id} "
        f"using {input_data.work_item_path} as the local target artifact."
    )

"""Review runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewRunnerInput:
    work_item_id: str
    pr_number: int


def build_review_prompt(input_data: ReviewRunnerInput) -> str:
    return (
        "Act only as the review agent.\n"
        f"Review PR #{input_data.pr_number} for {input_data.work_item_id}."
    )

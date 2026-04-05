"""Review runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewRunnerInput:
    work_item_id: str
    pr_number: int
    pr_url: str | None = None


def build_review_prompt(input_data: ReviewRunnerInput) -> str:
    prompt = f"Act only as the review agent.\nReview PR #{input_data.pr_number} for {input_data.work_item_id}."
    if input_data.pr_url is not None:
        prompt += f"\nPR URL: {input_data.pr_url}"
    return prompt

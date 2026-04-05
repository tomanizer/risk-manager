"""Spec runner scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecRunnerInput:
    work_item_id: str
    blocked_reason: str


def build_spec_prompt(input_data: SpecRunnerInput) -> str:
    return f"Act only as the spec-resolution agent.\nResolve the blocker for {input_data.work_item_id}: {input_data.blocked_reason}"

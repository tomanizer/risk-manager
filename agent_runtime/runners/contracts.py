"""Typed runner invocation contracts for the repository runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RunnerName(str, Enum):
    PM = "pm"
    SPEC = "spec"
    CODING = "coding"
    REVIEW = "review"


@dataclass(frozen=True)
class RunnerExecution:
    runner_name: RunnerName
    work_item_id: str
    prompt: str
    metadata: dict[str, str] = field(default_factory=dict)

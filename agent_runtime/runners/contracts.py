"""Typed runner invocation contracts for the repository runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RunnerName(str, Enum):
    PM = "pm"
    SPEC = "spec"
    CODING = "coding"
    REVIEW = "review"


class RunnerDispatchStatus(str, Enum):
    PREPARED = "prepared"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RunnerExecution:
    runner_name: RunnerName
    work_item_id: str
    prompt: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RunnerResult:
    runner_name: RunnerName
    work_item_id: str
    status: RunnerDispatchStatus
    summary: str
    prompt: str
    details: dict[str, str] = field(default_factory=dict)
    outcome_status: str | None = None
    outcome_summary: str | None = None
    outcome_details: dict[str, str] = field(default_factory=dict)

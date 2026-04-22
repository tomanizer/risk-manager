"""Typed runner invocation contracts for the repository runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from alterraflow.backend_type import BackendType

__all__ = ["BackendType"]


class RunnerName(str, Enum):
    PM = "pm"
    SPEC = "spec"
    ISSUE_PLANNER = "issue_planner"
    CODING = "coding"
    REVIEW = "review"
    DRIFT_MONITOR = "drift_monitor"


class RunnerDispatchStatus(str, Enum):
    PREPARED = "prepared"
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    NEEDS_HUMAN = "needs_human"


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


@runtime_checkable
class RunnerProtocol(Protocol):
    """Common interface that all runner implementations must satisfy.

    The prepare/execute split mirrors the current stub pattern while
    providing the extension point that LangGraph nodes will wrap.

    - ``runner_name``: identifies the role
    - ``get_system_prompt``: returns the governed instruction document
    - ``prepare``: builds a result without calling an external agent
    - ``execute``: calls the underlying agent backend (async)
    """

    @property
    def runner_name(self) -> RunnerName: ...
    def get_system_prompt(self) -> str: ...
    def prepare(self, execution: RunnerExecution) -> RunnerResult: ...
    async def execute(self, execution: RunnerExecution) -> RunnerResult: ...

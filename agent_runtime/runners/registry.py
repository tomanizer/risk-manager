"""Runner registry — maps runner names to protocol implementations."""

from __future__ import annotations

from pathlib import Path

from .coding_runner import CodingRunner
from .contracts import RunnerName, RunnerProtocol
from .drift_monitor_runner import DriftMonitorRunner
from .issue_planner_runner import IssuePlannerRunner
from .pm_runner import PMRunner
from .review_runner import ReviewRunner
from .spec_runner import SpecRunner


def build_runner_registry(repo_root: Path) -> dict[RunnerName, RunnerProtocol]:
    """Construct all runner implementations for the given repository root.

    This is the single place where new runner roles are wired in.
    LangGraph migration will wrap each entry as a graph node.
    """
    return {
        RunnerName.PM: PMRunner(repo_root),
        RunnerName.SPEC: SpecRunner(repo_root),
        RunnerName.CODING: CodingRunner(repo_root),
        RunnerName.REVIEW: ReviewRunner(repo_root),
        RunnerName.ISSUE_PLANNER: IssuePlannerRunner(repo_root),
        RunnerName.DRIFT_MONITOR: DriftMonitorRunner(repo_root),
    }

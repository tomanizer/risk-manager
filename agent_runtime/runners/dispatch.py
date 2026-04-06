"""Deterministic local dispatch for runner executions."""

from __future__ import annotations

from .coding_runner import dispatch_coding_execution
from .contracts import RunnerExecution, RunnerName, RunnerResult
from .drift_monitor_runner import dispatch_drift_monitor_execution
from .issue_planner_runner import dispatch_issue_planner_execution
from .pm_runner import dispatch_pm_execution
from .review_runner import dispatch_review_execution
from .spec_runner import dispatch_spec_execution


def dispatch_runner_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is RunnerName.PM:
        return dispatch_pm_execution(execution)
    if execution.runner_name is RunnerName.SPEC:
        return dispatch_spec_execution(execution)
    if execution.runner_name is RunnerName.ISSUE_PLANNER:
        return dispatch_issue_planner_execution(execution)
    if execution.runner_name is RunnerName.CODING:
        return dispatch_coding_execution(execution)
    if execution.runner_name is RunnerName.REVIEW:
        return dispatch_review_execution(execution)
    if execution.runner_name is RunnerName.DRIFT_MONITOR:
        return dispatch_drift_monitor_execution(execution)
    raise RuntimeError(f"unsupported runner dispatch target: {execution.runner_name}")

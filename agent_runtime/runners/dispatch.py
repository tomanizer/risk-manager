"""Deterministic local dispatch for runner executions."""

from __future__ import annotations

import time

from agent_runtime.telemetry import record_runner_dispatch, runner_span

from .coding_runner import dispatch_coding_execution
from .contracts import RunnerExecution, RunnerName, RunnerResult
from .pm_runner import dispatch_pm_execution
from .review_runner import dispatch_review_execution
from .spec_runner import dispatch_spec_execution


def dispatch_runner_execution(execution: RunnerExecution) -> RunnerResult:
    runner_name = execution.runner_name.value
    run_id = execution.metadata.get("run_id")
    start = time.monotonic()

    with runner_span(runner_name, execution.work_item_id, run_id=run_id) as span:
        if execution.runner_name is RunnerName.PM:
            result = dispatch_pm_execution(execution)
        elif execution.runner_name is RunnerName.SPEC:
            result = dispatch_spec_execution(execution)
        elif execution.runner_name is RunnerName.CODING:
            result = dispatch_coding_execution(execution)
        elif execution.runner_name is RunnerName.REVIEW:
            result = dispatch_review_execution(execution)
        else:
            raise RuntimeError(f"unsupported runner dispatch target: {execution.runner_name}")

        outcome = result.outcome_status or result.status.value
        if span is not None:
            span.set_attribute("runner.outcome_status", outcome)

    duration = time.monotonic() - start
    record_runner_dispatch(runner_name, outcome, duration)
    return result

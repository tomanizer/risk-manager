"""Parallel dispatch engine for the runtime orchestrator.

Wires ``decide_all_actions`` into the poll loop so that multiple work items
can advance concurrently, each in its own isolated git worktree.

The concurrency budget is configurable via ``RuntimeDefaults.max_concurrent_runs``
(default 3).  Items that already have an active worktree lease are skipped to
prevent double-dispatch.

Each eligible decision is dispatched in a separate thread.  The supervisor
collects all results and returns an aggregate payload.  The loop control
decision is based on the most actionable single-item result so that the
existing ``classify_loop_payload`` logic remains authoritative.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Sequence

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.graph import _dispatch_with_timeout
from agent_runtime.orchestrator.pr_publication import maybe_publish_completed_coding_run
from agent_runtime.orchestrator.worktree_manager import (
    allocate_worktree,
    bind_worktree_to_execution,
    has_reusable_active_worktree_lease,
)
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerResult
from agent_runtime.storage.sqlite import (
    WorkflowRunRecord,
    load_workflow_run,
    mark_workflow_run_running,
    record_workflow_outcome,
    upsert_workflow_run,
)

from .state import NextActionType, RuntimeSnapshot, TransitionDecision
from .transitions import decide_all_actions

_DISPATCHABLE_ACTIONS = {
    NextActionType.RUN_PM,
    NextActionType.RUN_SPEC,
    NextActionType.RUN_CODING,
    NextActionType.RUN_REVIEW,
}

_log = logging.getLogger(__name__)


def _dispatch_one(
    defaults: RuntimeDefaults,
    snapshot: RuntimeSnapshot,
    decision: TransitionDecision,
) -> dict[str, object]:
    """Dispatch a single decision and return its result payload."""
    existing_run = load_workflow_run(defaults.state_db_path, decision.work_item_id) if decision.work_item_id else None
    if existing_run is not None and existing_run.runner_status in ("failed", "timed_out"):
        retry_count = existing_run.retry_count + 1
    elif existing_run is not None:
        retry_count = existing_run.retry_count
    else:
        retry_count = 0

    execution_or_none = build_runner_execution(snapshot, decision)
    if execution_or_none is None:
        raise RuntimeError(f"Could not build runner execution for decision {decision.action.value} / {decision.work_item_id}")
    execution = execution_or_none
    worktree_lease = allocate_worktree(defaults, defaults.state_db_path, execution)
    execution = bind_worktree_to_execution(execution, worktree_lease)

    if decision.work_item_id is not None:
        mark_workflow_run_running(defaults.state_db_path, decision.work_item_id, retry_count)

    from dataclasses import replace as _replace

    runner_result: RunnerResult
    try:
        runner_result = _dispatch_with_timeout(execution, defaults)
    except Exception as exc:
        _log.error("Runner %s for %s raised an exception: %s", execution.runner_name.value, execution.work_item_id, exc, exc_info=True)
        runner_result = RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Runner raised an unexpected exception: {exc}",
            prompt=execution.prompt,
            details={**execution.metadata, "exception_type": type(exc).__name__},
        )

    pr_publication = maybe_publish_completed_coding_run(defaults.repo_root, execution, runner_result)
    if pr_publication is not None:
        pub_details = {**runner_result.details, "pr_publication_status": pr_publication.status}
        pub_outcome = {**runner_result.outcome_details, **pr_publication.details}
        if pr_publication.pr_number is not None:
            pub_details["pr_number"] = str(pr_publication.pr_number)
            pub_outcome["pr_number"] = str(pr_publication.pr_number)
        if pr_publication.pr_url is not None:
            pub_details["pr_url"] = pr_publication.pr_url
            pub_outcome["pr_url"] = pr_publication.pr_url
        runner_result = _replace(runner_result, details=pub_details, outcome_details=pub_outcome)

    if decision.work_item_id is not None:
        pr_number = None
        branch_name = None
        for pr in snapshot.pull_requests:
            if pr.work_item_id == decision.work_item_id:
                pr_number = pr.number
                branch_name = pr.head_ref_name
                break
        if pr_publication is not None and pr_publication.pr_number is not None:
            pr_number = pr_publication.pr_number
        existing_run_post = load_workflow_run(defaults.state_db_path, decision.work_item_id)
        upsert_workflow_run(
            defaults.state_db_path,
            WorkflowRunRecord(
                work_item_id=decision.work_item_id,
                run_id=execution.metadata.get("run_id"),
                branch_name=branch_name,
                pr_number=pr_number,
                status=decision.action.value,
                blocked_reason=decision.reason if decision.action is NextActionType.RUN_SPEC else None,
                last_action=decision.action.value,
                runner_name=execution.runner_name.value,
                runner_status=runner_result.status.value,
                outcome_status=existing_run_post.outcome_status if existing_run_post else None,
                outcome_summary=existing_run_post.outcome_summary if existing_run_post else None,
                retry_count=retry_count,
                details={**dict(decision.metadata), **dict(execution.metadata)},
                result={
                    "summary": runner_result.summary,
                    "prompt": runner_result.prompt,
                    "details": dict(runner_result.details),
                    "outcome_status": runner_result.outcome_status,
                    "outcome_summary": runner_result.outcome_summary,
                    "outcome_details": runner_result.outcome_details,
                },
                outcome_details=existing_run_post.outcome_details if existing_run_post else {},
                completed_at=existing_run_post.completed_at if existing_run_post else None,
            ),
        )
        if (
            runner_result.status is RunnerDispatchStatus.COMPLETED
            and runner_result.outcome_status is not None
            and execution.metadata.get("run_id") is not None
        ):
            record_workflow_outcome(
                defaults.state_db_path,
                execution.metadata["run_id"],
                runner_result.outcome_status,
                runner_result.outcome_summary or runner_result.summary,
                dict(runner_result.outcome_details),
            )

    return {
        "action": decision.action.value,
        "work_item_id": decision.work_item_id,
        "reason": decision.reason,
        "retry_count": retry_count,
        "runner_result": {
            "name": runner_result.runner_name.value,
            "status": runner_result.status.value,
            "summary": runner_result.summary,
            "outcome_status": runner_result.outcome_status,
            "outcome_summary": runner_result.outcome_summary,
            "details": runner_result.details,
            "outcome_details": runner_result.outcome_details,
            "prompt": runner_result.prompt,
        },
    }


def _has_active_lease(defaults: RuntimeDefaults, snapshot: RuntimeSnapshot, decision: TransitionDecision) -> bool:
    """Return True if the work item already has a reusable active worktree lease."""
    if decision.work_item_id is None:
        return False
    try:
        execution = build_runner_execution(snapshot, decision)
    except RuntimeError:
        return False
    if execution is None:
        return False
    return has_reusable_active_worktree_lease(defaults, defaults.state_db_path, execution)


def run_parallel_step(
    defaults: RuntimeDefaults,
    snapshot: RuntimeSnapshot,
) -> dict[str, object]:
    """Evaluate all eligible decisions and dispatch them concurrently.

    Returns an aggregate payload compatible with ``classify_loop_payload``.
    The ``runner_result`` key carries the *first* non-prepared result so the
    existing loop-control logic continues to work correctly.
    """
    all_decisions = decide_all_actions(snapshot)

    dispatchable = [d for d in all_decisions if d.action in _DISPATCHABLE_ACTIONS and not _has_active_lease(defaults, snapshot, d)][
        : defaults.max_concurrent_runs
    ]

    if not dispatchable:
        # Fall back to reporting the first non-dispatchable decision
        if all_decisions:
            first = all_decisions[0]
            return {
                "action": first.action.value,
                "work_item_id": first.work_item_id,
                "reason": first.reason,
                "retry_count": 0,
                "runner_result": None,
                "parallel_results": [],
                "work_item_count": len(snapshot.work_items),
                "pull_request_count": len(snapshot.pull_requests),
                "warnings": list(snapshot.warnings),
            }
        return {
            "action": NextActionType.NOOP.value,
            "work_item_id": None,
            "reason": "no eligible work items for parallel dispatch",
            "retry_count": 0,
            "runner_result": None,
            "parallel_results": [],
            "work_item_count": len(snapshot.work_items),
            "pull_request_count": len(snapshot.pull_requests),
            "warnings": list(snapshot.warnings),
        }

    parallel_results: list[dict[str, object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(dispatchable)) as executor:
        futures = {executor.submit(_dispatch_one, defaults, snapshot, d): d for d in dispatchable}
        for future in concurrent.futures.as_completed(futures):
            decision = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                _log.error("Parallel dispatch for %s raised: %s", decision.work_item_id, exc, exc_info=True)
                result = {
                    "action": decision.action.value,
                    "work_item_id": decision.work_item_id,
                    "reason": decision.reason,
                    "retry_count": 0,
                    "runner_result": {"status": "failed", "summary": str(exc)},
                }
            parallel_results.append(result)

    # Choose the most actionable single result for classify_loop_payload
    primary = _pick_primary_result(parallel_results)
    primary["parallel_results"] = parallel_results
    primary["work_item_count"] = len(snapshot.work_items)
    primary["pull_request_count"] = len(snapshot.pull_requests)
    primary["warnings"] = list(snapshot.warnings)
    return primary


_STATUS_PRIORITY = {"failed": 0, "timed_out": 1, "completed": 2, "prepared": 3}


def _pick_primary_result(results: Sequence[dict[str, object]]) -> dict[str, object]:
    """Return the result with the highest urgency for loop-control decisions."""
    if not results:
        return {
            "action": NextActionType.NOOP.value,
            "work_item_id": None,
            "reason": "no parallel results",
            "retry_count": 0,
            "runner_result": None,
        }

    def _urgency(r: dict[str, object]) -> int:
        rr = r.get("runner_result")
        if not isinstance(rr, dict):
            return 99
        return _STATUS_PRIORITY.get(str(rr.get("status") or ""), 99)

    best: dict[str, object] = results[0]
    best_score = _urgency(best)
    for r in results[1:]:
        score = _urgency(r)
        if score < best_score:
            best = r
            best_score = score
    return dict(best)

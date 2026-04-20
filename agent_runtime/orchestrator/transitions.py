"""Simple transition logic for the first runtime orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
import re

from agent_runtime.storage.sqlite import WorkflowRunRecord

from .state import (
    BacklogMaterializationSnapshot,
    NextActionType,
    PullRequestSnapshot,
    RuntimeSnapshot,
    TransitionDecision,
    WorkItemSnapshot,
    WorkItemStage,
)

_PENDING_CI_STATES = {"EXPECTED", "PENDING", "QUEUED", "IN_PROGRESS"}
_FAILING_CI_STATES = {"ACTION_REQUIRED", "CANCELLED", "ERROR", "FAILURE", "STALE", "STARTUP_FAILURE", "TIMED_OUT"}
_READY_MERGE_STATES = {"CLEAN", "HAS_HOOKS", "UNSTABLE"}
_PM_READY_OUTCOMES = {"ready"}
_PM_SPEC_OUTCOMES = {"blocked", "spec_required"}
_PM_ISSUE_PLANNER_OUTCOMES = {"split_required"}
_CODING_REPO_UPDATE_OUTCOMES = {"blocked", "completed", "needs_pm"}
_REVIEW_CODING_OUTCOMES = {"changes_requested"}
_REVIEW_REPO_UPDATE_OUTCOMES = {"blocked", "pass"}
_SPEC_REPO_UPDATE_OUTCOMES = {"clarified", "blocked", "split_required"}
_PRD_PATH_PATTERN = re.compile(r"docs/prds/[A-Za-z0-9_./-]+\.md")


def _parse_workflow_run_timestamp(timestamp: str | None) -> float | None:
    if timestamp is None:
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError:
        pass
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return None


def _workflow_run_recency_key(workflow_run: WorkflowRunRecord) -> tuple[int, float]:
    updated_timestamp = _parse_workflow_run_timestamp(getattr(workflow_run, "updated_at", None))
    if updated_timestamp is not None:
        return (1, updated_timestamp)
    completed_timestamp = _parse_workflow_run_timestamp(workflow_run.completed_at)
    if completed_timestamp is not None:
        return (0, completed_timestamp)
    return (-1, float("-inf"))


def _latest_workflow_runs_by_work_item(snapshot: RuntimeSnapshot) -> dict[str, WorkflowRunRecord]:
    latest_runs: dict[str, WorkflowRunRecord] = {}
    for workflow_run in snapshot.workflow_runs:
        current_latest = latest_runs.get(workflow_run.work_item_id)
        if current_latest is None or _workflow_run_recency_key(workflow_run) > _workflow_run_recency_key(current_latest):
            latest_runs[workflow_run.work_item_id] = workflow_run
    return latest_runs


def _dependencies_satisfied(item: WorkItemSnapshot, snapshot: RuntimeSnapshot) -> bool:
    completed_ids = {candidate.id for candidate in snapshot.work_items if candidate.stage is WorkItemStage.DONE}
    for dependency in item.dependencies:
        if dependency.startswith("WI-") and dependency not in completed_ids:
            return False
    return True


def _extract_prd_path(linked_prd: str | None) -> str | None:
    if linked_prd is None:
        return None
    match = _PRD_PATH_PATTERN.search(linked_prd)
    if match is None:
        return None
    return match.group(0)


def _work_item_changed_since_completion(item: WorkItemSnapshot, completed_at: str | None) -> bool:
    if completed_at is None:
        return True
    try:
        completed_timestamp = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return True
    try:
        return item.path.stat().st_mtime > completed_timestamp
    except OSError:
        return True


def _pull_request_changed_since_completion(pull_request_updated_at: str | None, completed_at: str | None) -> bool:
    if pull_request_updated_at is None or completed_at is None:
        return True
    try:
        pull_request_timestamp = datetime.fromisoformat(pull_request_updated_at.replace("Z", "+00:00")).timestamp()
        completed_timestamp = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return True
    return pull_request_timestamp > completed_timestamp


def _decision_from_completed_pm_outcome(
    work_item: WorkItemSnapshot,
    workflow_run: WorkflowRunRecord | None,
) -> TransitionDecision | None:
    if workflow_run is None:
        return None
    if workflow_run.last_action != NextActionType.RUN_PM.value:
        return None
    if workflow_run.runner_status != "completed":
        return None
    if workflow_run.outcome_status is None:
        return None
    if _work_item_changed_since_completion(work_item, workflow_run.completed_at):
        return None

    metadata = {
        "pm_outcome_status": workflow_run.outcome_status,
    }
    if workflow_run.run_id is not None:
        metadata["pm_run_id"] = workflow_run.run_id

    if workflow_run.outcome_status in _PM_READY_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.RUN_CODING,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary or "latest PM assessment marked the work item ready for implementation",
            target_path=work_item.path,
            metadata=metadata,
        )
    if workflow_run.outcome_status in _PM_SPEC_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.RUN_SPEC,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary or "latest PM assessment requires a spec or PRD update before coding can proceed",
            target_path=work_item.path,
            metadata=metadata,
        )
    if workflow_run.outcome_status in _PM_ISSUE_PLANNER_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.RUN_ISSUE_PLANNER,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary or "latest PM assessment requires the work item to be split before coding can proceed",
            target_path=work_item.path,
            metadata=metadata,
        )
    return None


def _decision_from_completed_spec_outcome(
    work_item: WorkItemSnapshot,
    workflow_run: WorkflowRunRecord | None,
) -> TransitionDecision | None:
    if workflow_run is None:
        return None
    if workflow_run.last_action != NextActionType.RUN_SPEC.value:
        return None
    if workflow_run.runner_status != "completed":
        return None
    if workflow_run.outcome_status is None:
        return None
    if _work_item_changed_since_completion(work_item, workflow_run.completed_at):
        return None

    metadata = {
        "spec_outcome_status": workflow_run.outcome_status,
    }
    if workflow_run.run_id is not None:
        metadata["spec_run_id"] = workflow_run.run_id

    if workflow_run.outcome_status in _SPEC_REPO_UPDATE_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.HUMAN_UPDATE_REPO,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary
            or f"latest spec resolution ({workflow_run.outcome_status}) requires a repo update before another agent run",
            target_path=work_item.path,
            metadata=metadata,
        )
    return None


def _decision_from_completed_review_outcome(
    work_item: WorkItemSnapshot,
    pull_request_updated_at: str | None,
    pr_number: int,
    workflow_run: WorkflowRunRecord | None,
) -> TransitionDecision | None:
    if workflow_run is None:
        return None
    if workflow_run.last_action != NextActionType.RUN_REVIEW.value:
        return None
    if workflow_run.runner_status != "completed":
        return None
    if workflow_run.outcome_status is None:
        return None
    if workflow_run.pr_number != pr_number:
        return None
    if _pull_request_changed_since_completion(pull_request_updated_at, workflow_run.completed_at):
        return None

    metadata = {
        "review_outcome_status": workflow_run.outcome_status,
    }
    if workflow_run.run_id is not None:
        metadata["review_run_id"] = workflow_run.run_id
    if workflow_run.pr_number is not None:
        metadata["pr_number"] = str(workflow_run.pr_number)

    if workflow_run.outcome_status in _REVIEW_CODING_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.RUN_CODING,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary or "latest review triage requires a coding follow-up",
            target_path=work_item.path,
            metadata=metadata,
        )
    if workflow_run.outcome_status in _REVIEW_REPO_UPDATE_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.HUMAN_UPDATE_REPO,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary or f"latest review triage ({workflow_run.outcome_status}) requires human attention",
            target_path=work_item.path,
            metadata=metadata,
        )
    return None


def _decision_from_completed_coding_outcome(
    work_item: WorkItemSnapshot,
    workflow_run: WorkflowRunRecord | None,
) -> TransitionDecision | None:
    if workflow_run is None:
        return None
    if workflow_run.last_action != NextActionType.RUN_CODING.value:
        return None
    if workflow_run.runner_status != "completed":
        return None
    if workflow_run.outcome_status is None:
        return None
    if _work_item_changed_since_completion(work_item, workflow_run.completed_at):
        return None

    metadata = {
        "coding_outcome_status": workflow_run.outcome_status,
    }
    if workflow_run.run_id is not None:
        metadata["coding_run_id"] = workflow_run.run_id

    if workflow_run.outcome_status in _CODING_REPO_UPDATE_OUTCOMES:
        return TransitionDecision(
            action=NextActionType.HUMAN_UPDATE_REPO,
            work_item_id=work_item.id,
            reason=workflow_run.outcome_summary or f"latest coding run ({workflow_run.outcome_status}) requires human attention",
            target_path=work_item.path,
            metadata=metadata,
        )
    return None


def _backlog_materialization_owner(
    snapshot: RuntimeSnapshot,
    finding: BacklogMaterializationSnapshot,
) -> WorkItemSnapshot | None:
    stage_priority = {
        WorkItemStage.DONE: 0,
        WorkItemStage.IN_PROGRESS: 1,
        WorkItemStage.BLOCKED: 2,
        WorkItemStage.READY: 3,
    }
    candidates = [work_item for work_item in snapshot.work_items if _extract_prd_path(work_item.linked_prd) == finding.source_path]
    if not candidates:
        return None
    return sorted(candidates, key=lambda work_item: (stage_priority[work_item.stage], work_item.id))[0]


def _decision_from_backlog_materialization(snapshot: RuntimeSnapshot) -> TransitionDecision | None:
    for finding in snapshot.backlog_materialization:
        owner = _backlog_materialization_owner(snapshot, finding)
        if owner is None:
            continue
        return TransitionDecision(
            action=NextActionType.RUN_ISSUE_PLANNER,
            work_item_id=owner.id,
            reason=finding.message,
            target_path=owner.path,
            metadata={
                "backlog_trigger": "missing_decomposed_work_items",
                "backlog_source_prd": finding.source_path,
                "missing_work_item_ids": ",".join(finding.related_paths),
            },
        )
    return None


def _decide_for_work_item(
    work_item: WorkItemSnapshot,
    pull_request: PullRequestSnapshot | None,
    workflow_run: WorkflowRunRecord | None,
) -> TransitionDecision:
    """Evaluate the transition for a single eligible work item.

    Shared core used by both ``decide_next_action`` (first-match) and
    ``decide_all_actions`` (full-scan).
    """
    if pull_request is None:
        spec_outcome = _decision_from_completed_spec_outcome(work_item, workflow_run)
        if spec_outcome is not None:
            return spec_outcome
        coding_outcome = _decision_from_completed_coding_outcome(work_item, workflow_run)
        if coding_outcome is not None:
            return coding_outcome
        pm_outcome = _decision_from_completed_pm_outcome(work_item, workflow_run)
        if pm_outcome is not None:
            return pm_outcome
        return TransitionDecision(
            action=NextActionType.RUN_PM,
            work_item_id=work_item.id,
            reason="ready item has no active PR; PM should issue or refresh the implementation brief",
            target_path=work_item.path,
        )

    review_outcome = _decision_from_completed_review_outcome(
        work_item,
        pull_request.updated_at,
        pull_request.number,
        workflow_run,
    )
    if review_outcome is not None:
        return review_outcome
    pr_meta = {"pr_number": str(pull_request.number), "pr_url": pull_request.url or ""}
    if pull_request.has_new_review_comments or pull_request.unresolved_review_threads > 0:
        return TransitionDecision(
            action=NextActionType.RUN_REVIEW,
            work_item_id=work_item.id,
            reason="PR has unresolved review feedback that should be triaged",
            target_path=work_item.path,
            metadata=pr_meta,
        )
    if pull_request.is_draft:
        return TransitionDecision(
            action=NextActionType.WAIT_FOR_REVIEWS,
            work_item_id=work_item.id,
            reason="draft PR is open and waiting for external review feedback",
            target_path=work_item.path,
            metadata=pr_meta,
        )
    if pull_request.ci_status in _FAILING_CI_STATES:
        return TransitionDecision(
            action=NextActionType.RUN_CODING,
            work_item_id=work_item.id,
            reason="PR checks are failing and need a coding pass",
            target_path=work_item.path,
            metadata={**pr_meta, "ci_status": pull_request.ci_status or ""},
        )
    if pull_request.ci_status in _PENDING_CI_STATES:
        return TransitionDecision(
            action=NextActionType.WAIT_FOR_REVIEWS,
            work_item_id=work_item.id,
            reason="PR checks are still running",
            target_path=work_item.path,
            metadata={**pr_meta, "ci_status": pull_request.ci_status or ""},
        )
    if pull_request.review_decision == "CHANGES_REQUESTED":
        return TransitionDecision(
            action=NextActionType.RUN_REVIEW,
            work_item_id=work_item.id,
            reason="PR has changes requested and should be triaged through review",
            target_path=work_item.path,
            metadata=pr_meta,
        )
    if pull_request.review_decision in {None, "REVIEW_REQUIRED"}:
        return TransitionDecision(
            action=NextActionType.WAIT_FOR_REVIEWS,
            work_item_id=work_item.id,
            reason="PR is open and waiting for review completion",
            target_path=work_item.path,
            metadata=pr_meta,
        )
    if pull_request.merge_state_status not in {None, *_READY_MERGE_STATES}:
        return TransitionDecision(
            action=NextActionType.RUN_CODING,
            work_item_id=work_item.id,
            reason="PR merge state requires branch updates or conflict resolution",
            target_path=work_item.path,
            metadata={**pr_meta, "merge_state_status": pull_request.merge_state_status or ""},
        )
    return TransitionDecision(
        action=NextActionType.HUMAN_MERGE,
        work_item_id=work_item.id,
        reason="PR is ready for human merge review",
        target_path=work_item.path,
        metadata=pr_meta,
    )


def _apply_drift_gate(snapshot: RuntimeSnapshot, decision: TransitionDecision) -> TransitionDecision:
    """Return WAIT_FOR_DRIFT_RESOLUTION if the decision is RUN_CODING and critical drift is present."""
    if decision.action is not NextActionType.RUN_CODING:
        return decision
    if snapshot.drift_critical_findings <= 0:
        return decision
    return TransitionDecision(
        action=NextActionType.WAIT_FOR_DRIFT_RESOLUTION,
        work_item_id=decision.work_item_id,
        reason=f"relay gated: {snapshot.drift_critical_findings} critical-severity drift finding(s) must be resolved before dispatching a coding run",
    )


def decide_next_action(snapshot: RuntimeSnapshot) -> TransitionDecision:
    prs_by_work_item = {pull_request.work_item_id: pull_request for pull_request in snapshot.pull_requests}
    workflow_runs_by_work_item = _latest_workflow_runs_by_work_item(snapshot)

    for work_item in snapshot.work_items:
        if work_item.stage is not WorkItemStage.READY:
            continue
        if not _dependencies_satisfied(work_item, snapshot):
            continue
        decision = _decide_for_work_item(
            work_item,
            prs_by_work_item.get(work_item.id),
            workflow_runs_by_work_item.get(work_item.id),
        )
        return _apply_drift_gate(snapshot, decision)

    backlog_decision = _decision_from_backlog_materialization(snapshot)
    if backlog_decision is not None:
        return backlog_decision

    return TransitionDecision(
        action=NextActionType.NOOP,
        work_item_id=None,
        reason="no ready work item is currently runnable",
    )


def decide_all_actions(snapshot: RuntimeSnapshot) -> tuple[TransitionDecision, ...]:
    """Return actionable decisions for *every* eligible work item.

    This is the entry point that a parallel scheduler or LangGraph
    ``Send`` API should use when dispatching concurrent agent runs.
    Items that are blocked, non-ready, or have unsatisfied
    dependencies are excluded.

    Unlike ``decide_next_action``, this does not short-circuit on the
    first match — it evaluates all ready work items in order.
    """
    prs_by_work_item = {pr.work_item_id: pr for pr in snapshot.pull_requests}
    workflow_runs_by_work_item = _latest_workflow_runs_by_work_item(snapshot)
    decisions: list[TransitionDecision] = []

    for work_item in snapshot.work_items:
        if work_item.stage is not WorkItemStage.READY:
            continue
        if not _dependencies_satisfied(work_item, snapshot):
            continue
        decision = _decide_for_work_item(
            work_item,
            prs_by_work_item.get(work_item.id),
            workflow_runs_by_work_item.get(work_item.id),
        )
        decisions.append(_apply_drift_gate(snapshot, decision))

    if not decisions:
        backlog_decision = _decision_from_backlog_materialization(snapshot)
        if backlog_decision is not None:
            return (backlog_decision,)

    return tuple(decisions)

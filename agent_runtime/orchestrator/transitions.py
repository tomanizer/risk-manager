"""Simple transition logic for the first runtime orchestrator."""

from __future__ import annotations

from .state import (
    NextActionType,
    RuntimeSnapshot,
    TransitionDecision,
    WorkItemSnapshot,
    WorkItemStage,
)

_PENDING_CI_STATES = {"EXPECTED", "PENDING", "QUEUED", "IN_PROGRESS"}
_FAILING_CI_STATES = {"ACTION_REQUIRED", "CANCELLED", "ERROR", "FAILURE", "STALE", "STARTUP_FAILURE", "TIMED_OUT"}
_READY_MERGE_STATES = {"CLEAN", "HAS_HOOKS", "UNSTABLE"}


def _dependencies_satisfied(item: WorkItemSnapshot, snapshot: RuntimeSnapshot) -> bool:
    completed_ids = {candidate.id for candidate in snapshot.work_items if candidate.stage is WorkItemStage.DONE}
    for dependency in item.dependencies:
        if dependency.startswith("WI-") and dependency not in completed_ids:
            return False
    return True


def decide_next_action(snapshot: RuntimeSnapshot) -> TransitionDecision:
    prs_by_work_item = {pull_request.work_item_id: pull_request for pull_request in snapshot.pull_requests}

    for work_item in snapshot.work_items:
        if work_item.stage is not WorkItemStage.READY:
            continue
        if not _dependencies_satisfied(work_item, snapshot):
            continue
        pull_request = prs_by_work_item.get(work_item.id)
        if pull_request is None:
            return TransitionDecision(
                action=NextActionType.RUN_PM,
                work_item_id=work_item.id,
                reason="ready item has no active PR; PM should issue or refresh the implementation brief",
                target_path=work_item.path,
            )
        if pull_request.has_new_review_comments or pull_request.unresolved_review_threads > 0:
            return TransitionDecision(
                action=NextActionType.RUN_REVIEW,
                work_item_id=work_item.id,
                reason="PR has unresolved review feedback that should be triaged",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                },
            )
        if pull_request.is_draft:
            return TransitionDecision(
                action=NextActionType.WAIT_FOR_REVIEWS,
                work_item_id=work_item.id,
                reason="draft PR is open and waiting for external review feedback",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                },
            )
        if pull_request.ci_status in _FAILING_CI_STATES:
            return TransitionDecision(
                action=NextActionType.RUN_CODING,
                work_item_id=work_item.id,
                reason="PR checks are failing and need a coding pass",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                    "ci_status": pull_request.ci_status or "",
                },
            )
        if pull_request.ci_status in _PENDING_CI_STATES:
            return TransitionDecision(
                action=NextActionType.WAIT_FOR_REVIEWS,
                work_item_id=work_item.id,
                reason="PR checks are still running",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                    "ci_status": pull_request.ci_status or "",
                },
            )
        if pull_request.review_decision == "CHANGES_REQUESTED":
            return TransitionDecision(
                action=NextActionType.RUN_REVIEW,
                work_item_id=work_item.id,
                reason="PR has changes requested and should be triaged through review",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                },
            )
        if pull_request.review_decision in {None, "REVIEW_REQUIRED"}:
            return TransitionDecision(
                action=NextActionType.WAIT_FOR_REVIEWS,
                work_item_id=work_item.id,
                reason="PR is open and waiting for review completion",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                },
            )
        if pull_request.merge_state_status not in {None, *_READY_MERGE_STATES}:
            return TransitionDecision(
                action=NextActionType.RUN_CODING,
                work_item_id=work_item.id,
                reason="PR merge state requires branch updates or conflict resolution",
                target_path=work_item.path,
                metadata={
                    "pr_number": str(pull_request.number),
                    "pr_url": pull_request.url or "",
                    "merge_state_status": pull_request.merge_state_status or "",
                },
            )
        return TransitionDecision(
            action=NextActionType.HUMAN_MERGE,
            work_item_id=work_item.id,
            reason="PR is ready for human merge review",
            target_path=work_item.path,
            metadata={
                "pr_number": str(pull_request.number),
                "pr_url": pull_request.url or "",
            },
        )

    return TransitionDecision(
        action=NextActionType.NOOP,
        work_item_id=None,
        reason="no ready work item is currently runnable",
    )

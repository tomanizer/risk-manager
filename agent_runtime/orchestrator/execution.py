"""Build typed runner invocations from relay decisions."""

from __future__ import annotations

from .state import NextActionType, PullRequestSnapshot, RuntimeSnapshot, TransitionDecision, WorkItemSnapshot
from ..runners.coding_runner import CodingRunnerInput, build_coding_prompt
from ..runners.contracts import RunnerExecution, RunnerName
from ..runners.pm_runner import PMRunnerInput, build_pm_prompt
from ..runners.review_runner import ReviewRunnerInput, build_review_prompt
from ..runners.spec_runner import SpecRunnerInput, build_spec_prompt


def _find_work_item(snapshot: RuntimeSnapshot, work_item_id: str) -> WorkItemSnapshot:
    for work_item in snapshot.work_items:
        if work_item.id == work_item_id:
            return work_item
    raise RuntimeError(f"runtime decision referenced unknown work item: {work_item_id}")


def _find_pull_request(snapshot: RuntimeSnapshot, work_item_id: str) -> PullRequestSnapshot | None:
    for pull_request in snapshot.pull_requests:
        if pull_request.work_item_id == work_item_id:
            return pull_request
    return None


def build_runner_execution(snapshot: RuntimeSnapshot, decision: TransitionDecision) -> RunnerExecution | None:
    if decision.work_item_id is None:
        return None

    work_item = _find_work_item(snapshot, decision.work_item_id)
    pull_request = _find_pull_request(snapshot, decision.work_item_id)
    default_base_ref = f"origin/{pull_request.head_ref_name}" if pull_request is not None and pull_request.head_ref_name else "origin/main"
    base_metadata = {
        **dict(decision.metadata),
        "base_ref": default_base_ref,
    }

    if decision.action is NextActionType.RUN_PM:
        pm_input = PMRunnerInput(
            work_item_id=work_item.id,
            work_item_path=str(work_item.path),
            linked_prd=work_item.linked_prd,
        )
        return RunnerExecution(
            runner_name=RunnerName.PM,
            work_item_id=work_item.id,
            prompt=build_pm_prompt(pm_input),
            metadata={**base_metadata, "target_path": str(work_item.path)},
        )

    if decision.action is NextActionType.RUN_SPEC:
        spec_input = SpecRunnerInput(
            work_item_id=work_item.id,
            blocked_reason=decision.reason,
            work_item_path=str(work_item.path),
        )
        return RunnerExecution(
            runner_name=RunnerName.SPEC,
            work_item_id=work_item.id,
            prompt=build_spec_prompt(spec_input),
            metadata={**base_metadata, "target_path": str(work_item.path)},
        )

    if decision.action is NextActionType.RUN_CODING:
        coding_input = CodingRunnerInput(
            work_item_id=work_item.id,
            task_summary=decision.reason,
            pr_number=pull_request.number if pull_request is not None else None,
            pr_url=pull_request.url if pull_request is not None else None,
            base_ref=base_metadata["base_ref"],
            drift_summary=snapshot.drift_summary_md,
        )
        metadata = {**base_metadata, "target_path": str(work_item.path)}
        if pull_request is not None:
            metadata["pr_number"] = str(pull_request.number)
            if pull_request.url is not None:
                metadata["pr_url"] = pull_request.url
        return RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id=work_item.id,
            prompt=build_coding_prompt(coding_input),
            metadata=metadata,
        )

    if decision.action is NextActionType.RUN_REVIEW:
        if pull_request is None:
            raise RuntimeError("review execution requires an attached pull request")
        review_input = ReviewRunnerInput(
            work_item_id=work_item.id,
            pr_number=pull_request.number,
            pr_url=pull_request.url,
            base_ref=base_metadata["base_ref"],
        )
        metadata = {
            **base_metadata,
            "target_path": str(work_item.path),
            "pr_number": str(pull_request.number),
        }
        if pull_request.url is not None:
            metadata["pr_url"] = pull_request.url
        return RunnerExecution(
            runner_name=RunnerName.REVIEW,
            work_item_id=work_item.id,
            prompt=build_review_prompt(review_input),
            metadata=metadata,
        )

    return None

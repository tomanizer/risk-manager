"""Build typed runner invocations from relay decisions."""

from __future__ import annotations

from pathlib import Path

from agent_runtime.handoff_bundle import build_handoff_bundle

from .state import NextActionType, PullRequestSnapshot, RuntimeSnapshot, TransitionDecision, WorkItemSnapshot
from ..runners.coding_runner import CodingRunnerInput, build_coding_prompt
from ..runners.contracts import RunnerExecution, RunnerName
from ..runners.drift_monitor_runner import DriftMonitorRunnerInput, build_drift_monitor_prompt
from ..runners.issue_planner_runner import IssuePlannerRunnerInput, build_issue_planner_prompt
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


def _build_runtime_handoff(
    *,
    runner_name: RunnerName,
    work_item: WorkItemSnapshot,
    runtime_metadata: dict[str, str],
    pull_request: PullRequestSnapshot | None,
) -> tuple[str, str]:
    try:
        bundle = build_handoff_bundle(
            role=runner_name.value,
            work_item_path=work_item.path,
            runtime_metadata=runtime_metadata,
            pull_request=pull_request,
        )
    except RuntimeError as error:
        if "Could not infer repo root from work item path" not in str(error):
            raise
        # Temp-fixture and simulation work items can live outside a full repo layout.
        bundle = build_handoff_bundle(
            role=runner_name.value,
            work_item_path=work_item.path,
            runtime_metadata=runtime_metadata,
            pull_request=pull_request,
            repo_root=Path(work_item.path).resolve().parent,
        )
    return bundle.render_markdown(), bundle.to_json()


def build_runner_execution(snapshot: RuntimeSnapshot, decision: TransitionDecision) -> RunnerExecution | None:
    if decision.action is NextActionType.RUN_DRIFT_CHECK:
        drift_input = DriftMonitorRunnerInput(
            repo_root=str(decision.target_path or "."),
            focus_area=decision.metadata.get("focus_area"),
        )
        return RunnerExecution(
            runner_name=RunnerName.DRIFT_MONITOR,
            work_item_id=decision.work_item_id or "repo",
            prompt=build_drift_monitor_prompt(drift_input),
            metadata=dict(decision.metadata),
        )

    if decision.work_item_id is None:
        return None

    if decision.action is NextActionType.RUN_SPEC and decision.metadata.get("bootstrap_mode") == "prd_gap":
        spec_input = SpecRunnerInput(
            work_item_id=decision.work_item_id,
            blocked_reason=decision.reason,
            work_item_path=str(decision.target_path or decision.metadata.get("registry_path") or "."),
            linked_prd=decision.metadata.get("existing_prd_path") or None,
            bootstrap_capability=decision.metadata.get("capability_name") or None,
            target_prd_id=decision.metadata.get("target_prd_id") or None,
            registry_path=decision.metadata.get("registry_path") or None,
            next_slice=decision.metadata.get("next_slice") or None,
        )
        return RunnerExecution(
            runner_name=RunnerName.SPEC,
            work_item_id=decision.work_item_id,
            prompt=build_spec_prompt(spec_input),
            metadata={
                **dict(decision.metadata),
                "target_path": str(decision.target_path) if decision.target_path is not None else str(decision.metadata.get("registry_path") or "."),
            },
        )

    work_item = _find_work_item(snapshot, decision.work_item_id)
    pull_request = _find_pull_request(snapshot, decision.work_item_id)
    default_base_ref = f"origin/{pull_request.base_ref_name}" if pull_request is not None and pull_request.base_ref_name else "origin/main"
    base_metadata = {
        **dict(decision.metadata),
        "base_ref": default_base_ref,
    }

    if decision.action is NextActionType.RUN_PM:
        handoff_bundle_markdown, handoff_bundle_json = _build_runtime_handoff(
            runner_name=RunnerName.PM,
            work_item=work_item,
            runtime_metadata=base_metadata,
            pull_request=pull_request,
        )
        pm_input = PMRunnerInput(
            work_item_id=work_item.id,
            work_item_path=str(work_item.path),
            linked_prd=work_item.linked_prd,
            handoff_bundle_markdown=handoff_bundle_markdown,
        )
        return RunnerExecution(
            runner_name=RunnerName.PM,
            work_item_id=work_item.id,
            prompt=build_pm_prompt(pm_input),
            metadata={
                **base_metadata,
                "target_path": str(work_item.path),
                "handoff_bundle_json": handoff_bundle_json,
            },
        )

    if decision.action is NextActionType.RUN_SPEC:
        handoff_bundle_markdown, handoff_bundle_json = _build_runtime_handoff(
            runner_name=RunnerName.SPEC,
            work_item=work_item,
            runtime_metadata=base_metadata,
            pull_request=pull_request,
        )
        spec_input = SpecRunnerInput(
            work_item_id=work_item.id,
            blocked_reason=decision.reason,
            work_item_path=str(work_item.path),
            linked_prd=work_item.linked_prd,
            handoff_bundle_markdown=handoff_bundle_markdown,
        )
        return RunnerExecution(
            runner_name=RunnerName.SPEC,
            work_item_id=work_item.id,
            prompt=build_spec_prompt(spec_input),
            metadata={
                **base_metadata,
                "target_path": str(work_item.path),
                "handoff_bundle_json": handoff_bundle_json,
            },
        )

    if decision.action is NextActionType.RUN_ISSUE_PLANNER:
        handoff_bundle_markdown, handoff_bundle_json = _build_runtime_handoff(
            runner_name=RunnerName.ISSUE_PLANNER,
            work_item=work_item,
            runtime_metadata=base_metadata,
            pull_request=pull_request,
        )
        missing_work_item_ids = tuple(item_id.strip() for item_id in decision.metadata.get("missing_work_item_ids", "").split(",") if item_id.strip())
        issue_planner_input = IssuePlannerRunnerInput(
            work_item_id=work_item.id,
            split_reason=decision.reason,
            work_item_path=str(work_item.path),
            linked_prd=work_item.linked_prd,
            source_prd_path=decision.metadata.get("backlog_source_prd"),
            missing_work_item_ids=missing_work_item_ids,
            handoff_bundle_markdown=handoff_bundle_markdown,
        )
        return RunnerExecution(
            runner_name=RunnerName.ISSUE_PLANNER,
            work_item_id=work_item.id,
            prompt=build_issue_planner_prompt(issue_planner_input),
            metadata={
                **base_metadata,
                "target_path": str(work_item.path),
                "handoff_bundle_json": handoff_bundle_json,
            },
        )

    if decision.action is NextActionType.RUN_CODING:
        metadata = {**base_metadata, "target_path": str(work_item.path)}
        if pull_request is not None and pull_request.head_ref_name:
            metadata["pr_number"] = str(pull_request.number)
            metadata["pr_head_branch"] = pull_request.head_ref_name
            metadata["checkout_ref"] = f"origin/{pull_request.head_ref_name}"
            metadata["checkout_detached"] = "true"
            metadata["branch_owned_by_runtime"] = "false"
            if pull_request.url is not None:
                metadata["pr_url"] = pull_request.url
        handoff_bundle_markdown, handoff_bundle_json = _build_runtime_handoff(
            runner_name=RunnerName.CODING,
            work_item=work_item,
            runtime_metadata=metadata,
            pull_request=pull_request,
        )
        coding_input = CodingRunnerInput(
            work_item_id=work_item.id,
            task_summary=decision.reason,
            pr_number=pull_request.number if pull_request is not None else None,
            pr_url=pull_request.url if pull_request is not None else None,
            base_ref=metadata["base_ref"],
            pr_head_branch=pull_request.head_ref_name if pull_request is not None else None,
            drift_summary=snapshot.drift_summary_md,
            handoff_bundle_markdown=handoff_bundle_markdown,
        )
        metadata["handoff_bundle_json"] = handoff_bundle_json
        return RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id=work_item.id,
            prompt=build_coding_prompt(coding_input),
            metadata=metadata,
        )

    if decision.action is NextActionType.RUN_REVIEW:
        if pull_request is None:
            raise RuntimeError("review execution requires an attached pull request")
        if not pull_request.head_ref_name:
            raise RuntimeError("review execution requires a PR head branch name")
        metadata = {
            **base_metadata,
            "target_path": str(work_item.path),
            "pr_number": str(pull_request.number),
            "pr_head_branch": pull_request.head_ref_name,
            "checkout_ref": f"origin/{pull_request.head_ref_name}",
            "checkout_detached": "true",
            "branch_owned_by_runtime": "false",
        }
        if pull_request.url is not None:
            metadata["pr_url"] = pull_request.url
        handoff_bundle_markdown, handoff_bundle_json = _build_runtime_handoff(
            runner_name=RunnerName.REVIEW,
            work_item=work_item,
            runtime_metadata=metadata,
            pull_request=pull_request,
        )
        review_input = ReviewRunnerInput(
            work_item_id=work_item.id,
            pr_number=pull_request.number,
            pr_url=pull_request.url,
            base_ref=metadata["base_ref"],
            pr_head_branch=pull_request.head_ref_name,
            handoff_bundle_markdown=handoff_bundle_markdown,
        )
        metadata["handoff_bundle_json"] = handoff_bundle_json
        return RunnerExecution(
            runner_name=RunnerName.REVIEW,
            work_item_id=work_item.id,
            prompt=build_review_prompt(review_input),
            metadata=metadata,
        )

    return None

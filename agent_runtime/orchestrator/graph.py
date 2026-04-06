"""First orchestration entrypoint for the repository delivery relay."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path

from agent_runtime.config.defaults import RuntimeDefaults, build_defaults
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.pr_publication import maybe_publish_completed_coding_run
from agent_runtime.orchestrator.supervisor import (
    classify_loop_payload,
    record_supervisor_heartbeat,
    sleep_for_poll_interval,
    supervisor_lock,
)
from agent_runtime.orchestrator.worktree_manager import allocate_worktree, bind_worktree_to_execution, release_worktree
from agent_runtime.runners.contracts import RunnerDispatchStatus
from agent_runtime.runners.dispatch import dispatch_runner_execution
from agent_runtime.storage.sqlite import (
    WorkflowRunRecord,
    load_workflow_run,
    load_workflow_runs,
    record_workflow_outcome,
    upsert_workflow_run,
)

from .github_sync import fetch_pull_requests
from .state import NextActionType, RuntimeSnapshot
from .simulations import build_simulation_snapshot, simulation_names
from .transitions import decide_next_action
from .work_item_registry import load_work_items


def find_repo_root(start_path: Path) -> Path:
    search_path = start_path if start_path.is_dir() else start_path.parent
    for candidate in (search_path, *search_path.parents):
        if (candidate / "AGENTS.md").exists() and (candidate / "work_items").is_dir():
            return candidate
    raise RuntimeError("could not determine repository root from runtime location")


def build_runtime_snapshot(repo_root: Path, state_db_path: Path) -> RuntimeSnapshot:
    work_items, warnings = load_work_items(repo_root)
    pull_requests, github_warnings = fetch_pull_requests(repo_root, work_items)
    workflow_runs = load_workflow_runs(state_db_path)
    return RuntimeSnapshot(
        work_items=work_items,
        pull_requests=pull_requests,
        workflow_runs=workflow_runs,
        warnings=warnings + github_warnings,
    )


def run_runtime_step(
    defaults: RuntimeDefaults,
    snapshot: RuntimeSnapshot,
    *,
    should_build_execution: bool,
    should_dispatch: bool,
) -> dict[str, object]:
    decision = decide_next_action(snapshot)
    execution = build_runner_execution(snapshot, decision) if should_build_execution else None
    worktree_lease = None
    if should_dispatch and execution is not None:
        worktree_lease = allocate_worktree(defaults, defaults.state_db_path, execution)
        execution = bind_worktree_to_execution(execution, worktree_lease)
    runner_result = dispatch_runner_execution(execution) if should_dispatch and execution is not None else None
    pr_publication = maybe_publish_completed_coding_run(defaults.repo_root, execution, runner_result)
    if runner_result is not None and pr_publication is not None:
        publication_details = {
            **runner_result.details,
            "pr_publication_status": pr_publication.status,
        }
        publication_outcome_details = {
            **runner_result.outcome_details,
            **pr_publication.details,
        }
        if pr_publication.pr_number is not None:
            publication_details["pr_number"] = str(pr_publication.pr_number)
            publication_outcome_details["pr_number"] = str(pr_publication.pr_number)
        if pr_publication.pr_url is not None:
            publication_details["pr_url"] = pr_publication.pr_url
            publication_outcome_details["pr_url"] = pr_publication.pr_url
        runner_result = replace(
            runner_result,
            details=publication_details,
            outcome_details=publication_outcome_details,
        )

    if should_build_execution and decision.work_item_id is not None:
        pr_number = None
        branch_name = None
        for pull_request in snapshot.pull_requests:
            if pull_request.work_item_id == decision.work_item_id:
                pr_number = pull_request.number
                branch_name = pull_request.head_ref_name
                break
        if pr_publication is not None and pr_publication.pr_number is not None:
            pr_number = pr_publication.pr_number
        if pr_publication is not None and execution is not None and execution.metadata.get("branch_name") is not None:
            branch_name = execution.metadata["branch_name"]
        existing_run = load_workflow_run(defaults.state_db_path, decision.work_item_id)
        upsert_workflow_run(
            defaults.state_db_path,
            WorkflowRunRecord(
                work_item_id=decision.work_item_id,
                run_id=execution.metadata.get("run_id") if execution is not None else existing_run.run_id if existing_run is not None else None,
                branch_name=branch_name,
                pr_number=pr_number,
                status=decision.action.value,
                blocked_reason=decision.reason if decision.action is NextActionType.RUN_SPEC else None,
                last_action=decision.action.value
                if execution is not None
                else existing_run.last_action
                if existing_run is not None
                else decision.action.value,
                runner_name=execution.runner_name.value if execution is not None else existing_run.runner_name if existing_run is not None else None,
                runner_status=runner_result.status.value
                if runner_result is not None
                else existing_run.runner_status
                if existing_run is not None
                else None,
                outcome_status=existing_run.outcome_status if existing_run is not None else None,
                outcome_summary=existing_run.outcome_summary if existing_run is not None else None,
                details=(
                    {
                        **dict(decision.metadata),
                        **dict(execution.metadata),
                    }
                    if execution is not None
                    else dict(decision.metadata)
                ),
                result=(
                    {
                        "summary": runner_result.summary,
                        "prompt": runner_result.prompt,
                        "details": dict(runner_result.details),
                        "outcome_status": runner_result.outcome_status,
                        "outcome_summary": runner_result.outcome_summary,
                        "outcome_details": runner_result.outcome_details,
                    }
                    if runner_result is not None
                    else existing_run.result
                    if existing_run is not None
                    else {}
                ),
                outcome_details=existing_run.outcome_details if existing_run is not None else {},
                completed_at=existing_run.completed_at if existing_run is not None else None,
            ),
        )
        if (
            execution is not None
            and runner_result is not None
            and runner_result.status is RunnerDispatchStatus.COMPLETED
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
        "metadata": decision.metadata,
        "reason": decision.reason,
        "target_path": str(decision.target_path) if decision.target_path else None,
        "work_item_id": decision.work_item_id,
        "runner": (
            {
                "name": execution.runner_name.value,
                "prompt": execution.prompt,
                "metadata": execution.metadata,
            }
            if execution is not None
            else None
        ),
        "runner_result": (
            {
                "name": runner_result.runner_name.value,
                "status": runner_result.status.value,
                "summary": runner_result.summary,
                "prompt": runner_result.prompt,
                "details": runner_result.details,
                "outcome_status": runner_result.outcome_status,
                "outcome_summary": runner_result.outcome_summary,
                "outcome_details": runner_result.outcome_details,
            }
            if runner_result is not None
            else None
        ),
        "worktree": (
            {
                "run_id": worktree_lease.run_id,
                "branch_name": worktree_lease.branch_name,
                "base_ref": worktree_lease.base_ref,
                "path": worktree_lease.worktree_path,
                "status": worktree_lease.status,
            }
            if worktree_lease is not None
            else None
        ),
        "state_db_path": str(defaults.state_db_path) if should_build_execution else None,
        "pull_request_count": len(snapshot.pull_requests),
        "pr_publication": (
            {
                "status": pr_publication.status,
                "summary": pr_publication.summary,
                "pr_number": pr_publication.pr_number,
                "pr_url": pr_publication.pr_url,
                "details": pr_publication.details,
            }
            if pr_publication is not None
            else None
        ),
        "work_item_count": len(snapshot.work_items),
        "warnings": list(snapshot.warnings),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the repository agent runtime.")
    parser.add_argument(
        "--simulate",
        choices=simulation_names(),
        help="Run a built-in simulation scenario instead of reading the live repository state.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List the built-in simulation scenarios and exit.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Build the next runner invocation and persist the resulting workflow-run record.",
    )
    parser.add_argument(
        "--dispatch",
        action="store_true",
        help="Dispatch the next runner invocation through the local deterministic runner adapters and persist the result.",
    )
    parser.add_argument(
        "--release-run",
        metavar="RUN_ID",
        help="Release a previously allocated worktree lease by run id.",
    )
    parser.add_argument(
        "--complete-run",
        metavar="RUN_ID",
        help="Record the real outcome of a manually executed runner session.",
    )
    parser.add_argument(
        "--outcome-status",
        help="Outcome status to record for --complete-run, for example ready, blocked, split_required, or pass.",
    )
    parser.add_argument(
        "--summary",
        help="Human-reviewed summary to record for --complete-run.",
    )
    parser.add_argument(
        "--outcome-details-json",
        help="Optional JSON object with structured outcome details for --complete-run.",
    )
    parser.add_argument(
        "--release-after-complete",
        action="store_true",
        help="Release the run worktree immediately after recording its outcome.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one supervised dispatch cycle with lock and heartbeat persistence.",
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Run the supervised poll loop until a human gate or manual handoff stops it.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        help="Override the default supervisor poll interval.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        help="Maximum iterations for --poll before exiting.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_scenarios:
        print(json.dumps({"simulation_scenarios": simulation_names()}, indent=2))
        return 0

    repo_root = find_repo_root(Path(__file__).resolve())
    defaults = build_defaults(repo_root)
    if args.poll_interval_seconds is not None:
        defaults = replace(defaults, poll_interval_seconds=args.poll_interval_seconds)
    if args.release_run is not None:
        release_status = release_worktree(defaults, defaults.state_db_path, args.release_run)
        print(
            json.dumps(
                {
                    "released_run_id": args.release_run,
                    "release_status": release_status,
                    "state_db_path": str(defaults.state_db_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.complete_run is not None:
        if args.outcome_status is None or args.summary is None:
            raise RuntimeError("--complete-run requires both --outcome-status and --summary")

        outcome_details: dict[str, object] = {}
        if args.outcome_details_json is not None:
            try:
                parsed_details = json.loads(args.outcome_details_json)
            except json.JSONDecodeError as error:
                raise RuntimeError("--outcome-details-json must be valid JSON") from error
            if not isinstance(parsed_details, dict):
                raise RuntimeError("--outcome-details-json must decode to a JSON object")
            outcome_details = {str(key): value for key, value in parsed_details.items()}

        record = record_workflow_outcome(
            defaults.state_db_path,
            args.complete_run,
            args.outcome_status,
            args.summary,
            outcome_details,
        )
        completion_release_status: str | None = None
        if args.release_after_complete:
            completion_release_status = release_worktree(defaults, defaults.state_db_path, args.complete_run)
        print(
            json.dumps(
                {
                    "completed_run_id": args.complete_run,
                    "found": record is not None,
                    "outcome_status": record.outcome_status if record is not None else None,
                    "outcome_summary": record.outcome_summary if record is not None else None,
                    "release_status": completion_release_status,
                    "state_db_path": str(defaults.state_db_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.run_once or args.poll:
        mode = "poll" if args.poll else "run_once"
        with supervisor_lock(defaults.supervisor_lock_path) as lock_owner:
            iteration = 0
            while True:
                iteration += 1
                record_started_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
                snapshot = (
                    build_simulation_snapshot(args.simulate)
                    if args.simulate is not None
                    else build_runtime_snapshot(repo_root, defaults.state_db_path)
                )
                payload = run_runtime_step(
                    defaults,
                    snapshot,
                    should_build_execution=True,
                    should_dispatch=True,
                )
                payload["dispatch"] = True
                payload["execute"] = True
                payload["simulation"] = args.simulate
                loop_control = classify_loop_payload(payload, defaults.poll_interval_seconds)
                supervisor_status = "waiting" if loop_control.continue_polling and (loop_control.sleep_seconds or 0) > 0 else "idle"
                if not loop_control.continue_polling:
                    supervisor_status = "stopped"
                record_supervisor_heartbeat(
                    defaults,
                    status=supervisor_status,
                    lock_owner=lock_owner,
                    mode=mode,
                    payload=payload,
                    started_at=record_started_at,
                )
                if not args.poll or not loop_control.continue_polling:
                    payload["mode"] = mode
                    print(json.dumps(payload, indent=2, sort_keys=True))
                    return loop_control.exit_code
                if args.max_iterations is not None and iteration >= args.max_iterations:
                    payload["mode"] = mode
                    payload["poll_iterations"] = iteration
                    print(json.dumps(payload, indent=2, sort_keys=True))
                    return loop_control.exit_code
                sleep_for_poll_interval(loop_control.sleep_seconds or 0)

    snapshot = build_simulation_snapshot(args.simulate) if args.simulate is not None else build_runtime_snapshot(repo_root, defaults.state_db_path)
    payload = run_runtime_step(
        defaults,
        snapshot,
        should_build_execution=args.execute or args.dispatch,
        should_dispatch=args.dispatch,
    )
    payload["dispatch"] = args.dispatch
    payload["execute"] = args.execute or args.dispatch
    payload["simulation"] = args.simulate
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0

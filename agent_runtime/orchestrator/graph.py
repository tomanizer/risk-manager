"""First orchestration entrypoint for the repository delivery relay."""

from __future__ import annotations

import argparse
import concurrent.futures
from dataclasses import replace
from datetime import UTC, datetime
import json
import logging
from pathlib import Path

from agent_runtime.config.defaults import RuntimeDefaults, build_defaults
from agent_runtime.drift.backlog_materialization import build_backlog_materialization_report
from agent_runtime.notifications.slack import notify_human_gate, notify_runner_failed, send_morning_digest
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.prd_bootstrap import load_prd_bootstrap_candidates
from agent_runtime.orchestrator.pr_publication import maybe_publish_completed_coding_run
from agent_runtime.orchestrator.supervisor import (
    classify_loop_payload,
    record_supervisor_heartbeat,
    sleep_for_poll_interval,
    supervisor_lock,
)
from agent_runtime.orchestrator.worktree_manager import allocate_worktree, bind_worktree_to_execution, release_worktree
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from agent_runtime.runners.dispatch import dispatch_runner_execution
from agent_runtime.storage.sqlite import (
    WorkflowRunRecord,
    load_workflow_run,
    load_workflow_runs,
    mark_workflow_run_running,
    record_workflow_outcome,
    upsert_workflow_run,
)

from .github_sync import fetch_pull_requests
from .state import BacklogMaterializationSnapshot, NextActionType, PrdBootstrapSnapshot, RuntimeSnapshot, TransitionDecision
from .simulations import build_simulation_snapshot, simulation_names
from .transitions import decide_next_action
from .work_item_registry import load_work_items

logger = logging.getLogger(__name__)


def _runner_timeout_seconds(runner_name: RunnerName, defaults: RuntimeDefaults) -> int:
    if runner_name is RunnerName.CODING:
        return defaults.runner_timeout_seconds_coding
    return defaults.runner_timeout_seconds_default


def _dispatch_with_timeout(execution: RunnerExecution, defaults: RuntimeDefaults) -> RunnerResult:
    """Run dispatch_runner_execution in a thread with a wall-clock timeout.

    Returns the RunnerResult. On timeout, returns a TIMED_OUT RunnerResult so
    the supervisor can record it and apply retry logic without crashing.
    """
    timeout_seconds = _runner_timeout_seconds(execution.runner_name, defaults)
    # Use an explicit executor (not `with` block) so that on timeout we can call
    # shutdown(wait=False) and return immediately without blocking until the thread
    # finishes — which could be minutes for a long-running agent.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(dispatch_runner_execution, execution, state_db_path=defaults.state_db_path)
    try:
        result = future.result(timeout=timeout_seconds)
        executor.shutdown(wait=False)
        return result
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        logger.error(
            "Runner %s for %s timed out after %ds",
            execution.runner_name.value,
            execution.work_item_id,
            timeout_seconds,
        )
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.TIMED_OUT,
            summary=f"Runner {execution.runner_name.value} timed out after {timeout_seconds}s.",
            prompt=execution.prompt,
            details={**execution.metadata, "timeout_seconds": str(timeout_seconds)},
        )


def find_repo_root(start_path: Path) -> Path:
    search_path = start_path if start_path.is_dir() else start_path.parent
    for candidate in (search_path, *search_path.parents):
        if (candidate / "AGENTS.md").exists() and (candidate / "work_items").is_dir():
            return candidate
    raise RuntimeError("could not determine repository root from runtime location")


def build_governance_decision(repo_root: Path) -> TransitionDecision | None:
    """Run the drift suite; return a RUN_DRIFT_CHECK decision if net-new findings exist."""
    import subprocess
    import sys

    script_path = repo_root / "scripts" / "drift" / "run_all.py"
    if not script_path.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--fail-on-findings"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        return None
    return TransitionDecision(
        action=NextActionType.RUN_DRIFT_CHECK,
        work_item_id=None,
        reason="drift suite found net-new findings; repo should be cleaned before the next relay step",
        target_path=repo_root,
        metadata={"repo_root": str(repo_root), "governance_already_run": "true"},
    )


def build_runtime_snapshot(repo_root: Path, state_db_path: Path) -> RuntimeSnapshot:
    work_items, warnings = load_work_items(repo_root)
    pull_requests, github_warnings = fetch_pull_requests(repo_root, work_items)
    workflow_runs = load_workflow_runs(state_db_path)
    backlog_materialization_report = build_backlog_materialization_report(repo_root)
    backlog_materialization = tuple(
        BacklogMaterializationSnapshot(
            source_path=finding.source_path,
            related_paths=finding.related_paths,
            message=finding.message,
        )
        for finding in backlog_materialization_report.findings
        if finding.kind == "missing_decomposed_work_items"
    )
    prd_bootstrap = tuple(
        PrdBootstrapSnapshot(
            capability_name=candidate.capability_name,
            target_prd_id=candidate.target_prd_id,
            existing_prd_path=candidate.existing_prd_path,
            registry_path=candidate.registry_path,
            next_slice=candidate.next_slice,
            next_version_reason=candidate.next_version_reason,
        )
        for candidate in load_prd_bootstrap_candidates(repo_root)
    )
    # drift_critical_findings / drift_summary_md are intentionally not populated
    # here — running the full drift suite on every poll tick adds 5–10 s of latency.
    # Drift gating is handled by the --governance pre-step, which runs before the
    # snapshot/dispatch loop and returns early when critical findings are present.
    # These fields are reserved for a future lightweight inline check.
    return RuntimeSnapshot(
        work_items=work_items,
        pull_requests=pull_requests,
        workflow_runs=workflow_runs,
        warnings=warnings + github_warnings,
        backlog_materialization=backlog_materialization,
        prd_bootstrap=prd_bootstrap,
    )


# ---------------------------------------------------------------------------
# Notification helper (Iter 2)
# ---------------------------------------------------------------------------


def _emit_loop_notifications(
    payload: dict[str, object],
    loop_control_exit_code: int,
    loop_control_continue: bool,
    max_retries: int,
) -> None:
    """Fire Slack notifications for human gates and terminal failures."""
    action = str(payload.get("action") or "")
    if not loop_control_continue:
        if action in {"human_merge", "human_update_repo"}:
            work_item_id = str(payload.get("work_item_id") or "unknown")
            reason = str(payload.get("reason") or "")
            pr_url: str | None = None
            runner_result = payload.get("runner_result")
            if isinstance(runner_result, dict):
                details = runner_result.get("details")
                if isinstance(details, dict):
                    pr_url = str(details.get("pr_url", "")) or None
            notify_human_gate(action, work_item_id, reason, pr_url)
        elif loop_control_exit_code != 0:
            runner_result = payload.get("runner_result")
            if isinstance(runner_result, dict):
                work_item_id = str(payload.get("work_item_id") or "unknown")
                runner_name = str(runner_result.get("name") or "unknown")
                summary = str(runner_result.get("summary") or "")
                raw_retry = payload.get("retry_count")
                retry_count = int(raw_retry) if isinstance(raw_retry, int) else 0
                notify_runner_failed(work_item_id, runner_name, summary, retries_exhausted=retry_count >= max_retries)


# ---------------------------------------------------------------------------
# Core step
# ---------------------------------------------------------------------------


def run_runtime_step(
    defaults: RuntimeDefaults,
    snapshot: RuntimeSnapshot,
    *,
    should_build_execution: bool,
    should_dispatch: bool,
) -> dict[str, object]:
    decision = decide_next_action(snapshot)

    # Load existing run early to determine retry_count for this dispatch attempt.
    existing_run_pre = (
        load_workflow_run(defaults.state_db_path, decision.work_item_id) if should_build_execution and decision.work_item_id is not None else None
    )
    if existing_run_pre is not None and existing_run_pre.runner_status in ("failed", "timed_out"):
        retry_count = existing_run_pre.retry_count + 1
    elif existing_run_pre is not None:
        retry_count = existing_run_pre.retry_count
    else:
        retry_count = 0

    execution = build_runner_execution(snapshot, decision) if should_build_execution else None
    worktree_lease = None
    if should_dispatch and execution is not None:
        worktree_lease = allocate_worktree(defaults, defaults.state_db_path, execution)
        execution = bind_worktree_to_execution(execution, worktree_lease)

    runner_result = None
    if should_dispatch and execution is not None:
        # Write RUNNING status before the blocking dispatch so a crashed supervisor
        # can detect orphaned in-flight runs.
        if decision.work_item_id is not None:
            mark_workflow_run_running(defaults.state_db_path, decision.work_item_id, retry_count)
        try:
            runner_result = _dispatch_with_timeout(execution, defaults)
        except Exception as exc:
            logger.error(
                "Runner %s for %s raised unexpected exception: %s",
                execution.runner_name.value,
                execution.work_item_id,
                exc,
                exc_info=True,
            )
            runner_result = RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"Runner raised an unexpected exception: {exc}",
                prompt=execution.prompt,
                details={**execution.metadata, "exception_type": type(exc).__name__},
            )
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
                retry_count=retry_count,
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
        "retry_count": retry_count,
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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
    parser.add_argument(
        "--governance",
        action="store_true",
        help="Run the drift suite as a pre-step; emit a drift-check handoff if net-new findings are present.",
    )
    parser.add_argument(
        "--digest",
        action="store_true",
        help="Post a morning activity digest to Slack and exit.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_scenarios:
        print(json.dumps({"simulation_scenarios": simulation_names()}, indent=2))
        return 0

    try:
        from agent_runtime.telemetry import configure_telemetry

        configure_telemetry()
    except Exception:
        pass

    repo_root = find_repo_root(Path(__file__).resolve())
    defaults = build_defaults(repo_root)

    if args.poll_interval_seconds is not None:
        defaults = replace(defaults, poll_interval_seconds=args.poll_interval_seconds)

    # Iter 2: morning digest
    if args.digest:
        sent = send_morning_digest(defaults.state_db_path)
        print(json.dumps({"digest_sent": sent, "state_db_path": str(defaults.state_db_path)}, indent=2))
        return 0

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

                if getattr(args, "governance", False) and args.simulate is None:
                    governance_decision = build_governance_decision(repo_root)
                    if governance_decision is not None:
                        from .execution import build_runner_execution as _bre
                        from .state import RuntimeSnapshot as _RS

                        _empty = _RS(work_items=(), pull_requests=(), workflow_runs=(), warnings=())
                        _exec = _bre(_empty, governance_decision)
                        _result = dispatch_runner_execution(_exec, state_db_path=defaults.state_db_path) if _exec is not None else None
                        payload: dict[str, object] = {
                            "action": governance_decision.action.value,
                            "reason": governance_decision.reason,
                            "governance": True,
                            "dispatch": True,
                            "execute": True,
                            "simulation": args.simulate,
                            "mode": mode,
                            "runner": (
                                {"name": _exec.runner_name.value, "prompt": _exec.prompt, "metadata": _exec.metadata} if _exec is not None else None
                            ),
                            "runner_result": (
                                {
                                    "name": _result.runner_name.value,
                                    "status": _result.status.value,
                                    "summary": _result.summary,
                                    "outcome_status": _result.outcome_status,
                                    "outcome_summary": _result.outcome_summary,
                                }
                                if _result is not None
                                else None
                            ),
                        }
                        loop_control = classify_loop_payload(payload, defaults.poll_interval_seconds)
                        supervisor_status = "stopped"
                        record_supervisor_heartbeat(
                            defaults,
                            status=supervisor_status,
                            lock_owner=lock_owner,
                            mode=mode,
                            payload=payload,
                            started_at=record_started_at,
                        )
                        print(json.dumps(payload, indent=2, sort_keys=True))
                        return loop_control.exit_code

                try:
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
                except Exception as exc:
                    logger.error("Poll iteration %d raised an unexpected exception: %s", iteration, exc, exc_info=True)
                    record_supervisor_heartbeat(
                        defaults,
                        status="waiting",
                        lock_owner=lock_owner,
                        mode=mode,
                        started_at=record_started_at,
                    )
                    if not args.poll:
                        return 1
                    sleep_for_poll_interval(defaults.poll_interval_seconds)
                    continue
                payload["dispatch"] = True
                payload["execute"] = True
                payload["simulation"] = args.simulate
                loop_control = classify_loop_payload(
                    payload,
                    defaults.poll_interval_seconds,
                    max_retries=defaults.runner_max_retries,
                )
                _emit_loop_notifications(payload, loop_control.exit_code, loop_control.continue_polling, defaults.runner_max_retries)
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

    if args.governance and args.simulate is None:
        governance_decision = build_governance_decision(repo_root)
        if governance_decision is not None:
            from .execution import build_runner_execution
            from .state import RuntimeSnapshot as _RS

            empty_snapshot = _RS(work_items=(), pull_requests=(), workflow_runs=(), warnings=())
            execution = build_runner_execution(empty_snapshot, governance_decision)
            runner_result = (
                dispatch_runner_execution(execution, state_db_path=defaults.state_db_path) if args.dispatch and execution is not None else None
            )
            governance_payload: dict[str, object] = {
                "action": governance_decision.action.value,
                "reason": governance_decision.reason,
                "governance": True,
                "dispatch": args.dispatch,
                "execute": args.execute or args.dispatch,
                "simulation": None,
                "runner": (
                    {"name": execution.runner_name.value, "prompt": execution.prompt, "metadata": execution.metadata}
                    if execution is not None
                    else None
                ),
                "runner_result": (
                    {
                        "name": runner_result.runner_name.value,
                        "status": runner_result.status.value,
                        "summary": runner_result.summary,
                        "outcome_status": runner_result.outcome_status,
                        "outcome_summary": runner_result.outcome_summary,
                    }
                    if runner_result is not None
                    else None
                ),
            }
            print(json.dumps(governance_payload, indent=2, sort_keys=True))
            return 0

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
    payload["governance"] = getattr(args, "governance", False)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0

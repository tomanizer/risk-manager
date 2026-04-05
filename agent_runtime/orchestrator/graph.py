"""First orchestration entrypoint for the repository delivery relay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_runtime.config.defaults import build_defaults
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.worktree_manager import allocate_worktree, bind_worktree_to_execution, release_worktree
from agent_runtime.runners.dispatch import dispatch_runner_execution
from agent_runtime.storage.sqlite import WorkflowRunRecord, upsert_workflow_run

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


def build_runtime_snapshot(repo_root: Path) -> RuntimeSnapshot:
    work_items, warnings = load_work_items(repo_root)
    pull_requests, github_warnings = fetch_pull_requests(repo_root, work_items)
    return RuntimeSnapshot(
        work_items=work_items,
        pull_requests=pull_requests,
        warnings=warnings + github_warnings,
    )


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
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_scenarios:
        print(json.dumps({"simulation_scenarios": simulation_names()}, indent=2))
        return 0

    repo_root = find_repo_root(Path(__file__).resolve())
    defaults = build_defaults(repo_root)
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

    snapshot = build_simulation_snapshot(args.simulate) if args.simulate is not None else build_runtime_snapshot(repo_root)
    decision = decide_next_action(snapshot)
    should_build_execution = args.execute or args.dispatch
    execution = build_runner_execution(snapshot, decision) if should_build_execution else None
    worktree_lease = None
    if args.dispatch and execution is not None:
        worktree_lease = allocate_worktree(defaults, defaults.state_db_path, execution)
        execution = bind_worktree_to_execution(execution, worktree_lease)
    runner_result = dispatch_runner_execution(execution) if args.dispatch and execution is not None else None

    if should_build_execution and decision.work_item_id is not None:
        pr_number = None
        branch_name = None
        for pull_request in snapshot.pull_requests:
            if pull_request.work_item_id == decision.work_item_id:
                pr_number = pull_request.number
                branch_name = pull_request.head_ref_name
                break
        upsert_workflow_run(
            defaults.state_db_path,
            WorkflowRunRecord(
                work_item_id=decision.work_item_id,
                branch_name=branch_name,
                pr_number=pr_number,
                status=decision.action.value,
                blocked_reason=decision.reason if decision.action is NextActionType.RUN_SPEC else None,
                last_action=decision.action.value,
                runner_name=execution.runner_name.value if execution is not None else None,
                runner_status=runner_result.status.value if runner_result is not None else None,
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
                    }
                    if runner_result is not None
                    else {}
                ),
            ),
        )

    print(
        json.dumps(
            {
                "action": decision.action.value,
                "dispatch": args.dispatch,
                "execute": args.execute,
                "simulation": args.simulate,
                "work_item_id": decision.work_item_id,
                "reason": decision.reason,
                "target_path": str(decision.target_path) if decision.target_path else None,
                "metadata": decision.metadata,
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
                "work_item_count": len(snapshot.work_items),
                "warnings": list(snapshot.warnings),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0

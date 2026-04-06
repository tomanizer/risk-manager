"""Tests for the first orchestrator transition logic."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any
from unittest.mock import patch

from agent_runtime.orchestrator.github_sync import (
    _extract_pull_request_page,
    build_pull_request_snapshots,
    parse_github_remote,
)
from agent_runtime.orchestrator.state import (
    NextActionType,
    PullRequestSnapshot,
    RuntimeSnapshot,
    WorkItemSnapshot,
    WorkItemStage,
)
from agent_runtime.orchestrator.graph import find_repo_root
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.simulations import build_simulation_snapshot, simulation_names
from agent_runtime.orchestrator.transitions import decide_next_action
from agent_runtime.orchestrator.work_item_registry import load_work_items
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerName
from agent_runtime.runners.dispatch import dispatch_runner_execution
from agent_runtime.storage.sqlite import (
    EXPECTED_WORKFLOW_RUN_COLUMNS,
    EXPECTED_WORKTREE_LEASE_COLUMNS,
    WorkflowRunRecord,
    initialize_database,
    load_workflow_run_by_run_id,
    load_workflow_run,
    load_workflow_runs,
    record_workflow_outcome,
    upsert_workflow_run,
)


def test_ready_item_without_pr_routes_to_pm() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.3-risk-summary-history-service",
                title="WI-1.1.3",
                path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
                stage=WorkItemStage.READY,
                dependencies=(),
            ),
        )
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.RUN_PM


def test_completed_pm_ready_outcome_routes_to_coding() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        os.utime(work_item_path, (1_000_000_000, 1_000_000_000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.4-risk-summary-core-service",
                    status="run_pm",
                    run_id="pm-wi-1-1-4-test-run",
                    last_action="run_pm",
                    runner_name="pm",
                    runner_status="completed",
                    outcome_status="ready",
                    outcome_summary="PM marked the work item ready for implementation.",
                    completed_at="2026-04-06 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_CODING
        assert decision.metadata["pm_outcome_status"] == "ready"
        assert decision.metadata["pm_run_id"] == "pm-wi-1-1-4-test-run"


def test_completed_pm_split_required_routes_to_spec() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        os.utime(work_item_path, (1_000_000_000, 1_000_000_000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.4-risk-summary-core-service",
                    status="run_pm",
                    run_id="pm-wi-1-1-4-test-run",
                    last_action="run_pm",
                    runner_name="pm",
                    runner_status="completed",
                    outcome_status="split_required",
                    outcome_summary="Need to split WI-1.1.4 before coding.",
                    completed_at="2026-04-06 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_SPEC
        assert decision.reason == "Need to split WI-1.1.4 before coding."


def test_completed_pm_outcome_is_ignored_after_work_item_changes() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        os.utime(work_item_path, None)

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.4-risk-summary-core-service",
                    status="run_pm",
                    run_id="pm-wi-1-1-4-test-run",
                    last_action="run_pm",
                    runner_name="pm",
                    runner_status="completed",
                    outcome_status="split_required",
                    outcome_summary="Need to split WI-1.1.4 before coding.",
                    completed_at="2020-01-01 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_PM


def test_completed_spec_outcome_routes_to_human_update_repo() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        os.utime(work_item_path, (1_000_000_000, 1_000_000_000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.4-risk-summary-core-service",
                    status="run_spec",
                    run_id="spec-wi-1-1-4-test-run",
                    last_action="run_spec",
                    runner_name="spec",
                    runner_status="completed",
                    outcome_status="clarified",
                    outcome_summary="Canon was clarified and the work item was updated.",
                    completed_at="2026-04-06 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.HUMAN_UPDATE_REPO
        assert decision.metadata["spec_outcome_status"] == "clarified"
        assert decision.metadata["spec_run_id"] == "spec-wi-1-1-4-test-run"


def test_completed_coding_outcome_routes_to_human_update_repo_when_no_pr_exists() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        os.utime(work_item_path, (1577872000, 1577872000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.4-risk-summary-core-service",
                    status="run_coding",
                    run_id="coding-wi-1-1-4-test-run",
                    last_action="run_coding",
                    runner_name="coding",
                    runner_status="completed",
                    outcome_status="completed",
                    outcome_summary="Implemented the requested slice and updated tests.",
                    completed_at="2020-01-01 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.HUMAN_UPDATE_REPO
        assert decision.metadata["coding_outcome_status"] == "completed"


def test_completed_coding_outcome_is_ignored_after_work_item_changes() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        os.utime(work_item_path, None)

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.4-risk-summary-core-service",
                    status="run_coding",
                    run_id="coding-wi-1-1-4-test-run",
                    last_action="run_coding",
                    runner_name="coding",
                    runner_status="completed",
                    outcome_status="completed",
                    outcome_summary="Implemented the requested slice and updated tests.",
                    completed_at="2020-01-01 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_PM


def test_open_pr_with_unresolved_reviews_routes_to_review() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.3-risk-summary-history-service",
                title="WI-1.1.3",
                path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
                stage=WorkItemStage.READY,
                dependencies=(),
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.3-risk-summary-history-service",
                number=42,
                is_draft=True,
                unresolved_review_threads=2,
                has_new_review_comments=True,
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.RUN_REVIEW


def test_open_pr_with_failing_checks_routes_to_coding() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.3-risk-summary-history-service",
                title="WI-1.1.3",
                path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
                stage=WorkItemStage.READY,
                dependencies=(),
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.3-risk-summary-history-service",
                number=42,
                is_draft=False,
                review_decision="APPROVED",
                ci_status="FAILURE",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.RUN_CODING


def test_open_pr_waits_for_review_until_approved() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.3-risk-summary-history-service",
                title="WI-1.1.3",
                path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
                stage=WorkItemStage.READY,
                dependencies=(),
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.3-risk-summary-history-service",
                number=42,
                is_draft=False,
                ci_status="SUCCESS",
                review_decision="REVIEW_REQUIRED",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.WAIT_FOR_REVIEWS


def test_built_in_simulation_scenarios_cover_expected_actions() -> None:
    expected_actions = {
        "ready-no-pr": NextActionType.RUN_PM,
        "blocked-dependency": NextActionType.RUN_PM,
        "draft-pr": NextActionType.WAIT_FOR_REVIEWS,
        "unresolved-review": NextActionType.RUN_REVIEW,
        "ready-for-merge": NextActionType.HUMAN_MERGE,
        "failing-ci-pr": NextActionType.RUN_CODING,
        "noop": NextActionType.NOOP,
    }

    assert set(simulation_names()) == set(expected_actions)

    for scenario_name, expected_action in expected_actions.items():
        snapshot = build_simulation_snapshot(scenario_name)
        decision = decide_next_action(snapshot)
        assert decision.action is expected_action


def test_repo_root_is_found_by_markers() -> None:
    repo_root = find_repo_root(Path(__file__).resolve())
    assert (repo_root / "AGENTS.md").exists()
    assert (repo_root / "work_items").is_dir()


def test_load_work_items_skips_unreadable_file_and_records_warning() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_root = Path(temp_dir)
        ready_dir = repo_root / "work_items" / "ready"
        ready_dir.mkdir(parents=True)
        valid_file = ready_dir / "WI-1-valid.md"
        valid_file.write_text("# WI-1\n\n## Linked PRD\nPRD-1\n", encoding="utf-8")
        unreadable_file = ready_dir / "WI-2-bad.md"
        unreadable_file.write_bytes(b"\xff\xfe\xfd")

        work_items, warnings = load_work_items(repo_root)

        assert len(work_items) == 1
        assert work_items[0].id == "WI-1-valid"
        assert len(warnings) == 1


def test_initialize_database_creates_expected_workflow_runs_schema() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"

        initialize_database(db_path)

        with sqlite3.connect(db_path) as connection:
            rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
            worktree_rows = connection.execute("PRAGMA table_info(worktree_leases)").fetchall()

        actual_columns = tuple(row[1] for row in rows)
        actual_worktree_columns = tuple(row[1] for row in worktree_rows)
        assert actual_columns == EXPECTED_WORKFLOW_RUN_COLUMNS
        assert actual_worktree_columns == EXPECTED_WORKTREE_LEASE_COLUMNS


def test_initialize_database_migrates_missing_updated_at_column() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE workflow_runs (
                    work_item_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    branch_name TEXT,
                    pr_number INTEGER,
                    status TEXT NOT NULL,
                    blocked_reason TEXT,
                    last_action TEXT,
                    runner_name TEXT,
                    runner_status TEXT,
                    outcome_status TEXT,
                    outcome_summary TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    outcome_details_json TEXT NOT NULL DEFAULT '{}',
                    completed_at TEXT
                );
                CREATE TABLE worktree_leases (
                    run_id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL,
                    runner_name TEXT NOT NULL,
                    branch_name TEXT NOT NULL,
                    base_ref TEXT NOT NULL,
                    worktree_path TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    released_at TEXT
                );
                """
            )
            connection.commit()

        initialize_database(db_path)

        with sqlite3.connect(db_path) as connection:
            rows = connection.execute("PRAGMA table_info(workflow_runs)").fetchall()

        actual_columns = tuple(row[1] for row in rows)
        assert actual_columns == EXPECTED_WORKFLOW_RUN_COLUMNS


def test_upsert_workflow_run_round_trips_extended_columns() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        record = WorkflowRunRecord(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            run_id="pm-wi-1-1-4-test-run",
            branch_name="codex/WI-1.1.4-risk-summary-core-service",
            pr_number=51,
            status="run_review",
            blocked_reason=None,
            last_action="run_review",
            runner_name="review",
            runner_status="prepared",
            details={"pr_url": "https://github.com/tomanizer/risk-manager/pull/51"},
            result={"summary": "Prepared review handoff.", "details": {"pr_url": "https://github.com/tomanizer/risk-manager/pull/51"}},
        )

        upsert_workflow_run(db_path, record)
        loaded = load_workflow_run(db_path, record.work_item_id)

        assert loaded is not None
        assert loaded.work_item_id == record.work_item_id
        assert loaded.run_id == record.run_id
        assert loaded.branch_name == record.branch_name
        assert loaded.pr_number == record.pr_number
        assert loaded.status == record.status
        assert loaded.last_action == record.last_action
        assert loaded.runner_name == record.runner_name
        assert loaded.runner_status == record.runner_status
        assert loaded.details == record.details
        assert loaded.result == record.result
        assert loaded.updated_at is not None


def test_record_workflow_outcome_updates_run_by_run_id() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        record = WorkflowRunRecord(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            run_id="pm-wi-1-1-4-test-run",
            branch_name="codex/WI-1.1.4-risk-summary-core-service",
            status="run_pm",
            last_action="run_pm",
            runner_name="pm",
            runner_status="prepared",
        )
        upsert_workflow_run(db_path, record)

        updated = record_workflow_outcome(
            db_path,
            "pm-wi-1-1-4-test-run",
            "split_required",
            "Need to split WI-1.1.4 before coding.",
            {"recommended_next_step": "update_work_item"},
        )

        assert updated is not None
        assert updated.runner_status == "completed"
        assert updated.outcome_status == "split_required"
        assert updated.outcome_summary == "Need to split WI-1.1.4 before coding."
        assert updated.outcome_details["recommended_next_step"] == "update_work_item"
        assert updated.completed_at is not None

        loaded = load_workflow_run_by_run_id(db_path, "pm-wi-1-1-4-test-run")
        assert loaded == updated


def test_record_workflow_outcome_returns_none_for_unknown_run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"

        updated = record_workflow_outcome(
            db_path,
            "missing-run",
            "blocked",
            "No matching run exists.",
        )

        assert updated is None


def test_load_workflow_runs_returns_updated_rows() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        record = WorkflowRunRecord(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            status="run_pm",
            run_id="pm-wi-1-1-4-test-run",
            last_action="run_pm",
            runner_name="pm",
            runner_status="completed",
            outcome_status="ready",
            outcome_summary="PM marked the work item ready for implementation.",
            completed_at="2026-04-06 10:00:00",
        )

        upsert_workflow_run(db_path, record)
        loaded = load_workflow_runs(db_path)

        assert len(loaded) == 1
        assert loaded[0].run_id == "pm-wi-1-1-4-test-run"
        assert loaded[0].updated_at is not None


def test_non_execution_decision_preserves_existing_pm_outcome_fields() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "runtime" / "state.db"
        existing = WorkflowRunRecord(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            status="run_pm",
            run_id="pm-wi-1-1-4-test-run",
            last_action="run_pm",
            runner_name="pm",
            runner_status="completed",
            outcome_status="split_required",
            outcome_summary="Need to split WI-1.1.4 before coding.",
            outcome_details={"recommended_next_step": "update_work_item"},
            completed_at="2026-04-06 10:00:00",
            result={"summary": "Prepared PM handoff."},
        )
        upsert_workflow_run(db_path, existing)

        updated = WorkflowRunRecord(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            run_id=existing.run_id,
            status=NextActionType.HUMAN_UPDATE_REPO.value,
            last_action=existing.last_action,
            runner_name=existing.runner_name,
            runner_status=existing.runner_status,
            details={"pm_outcome_status": "split_required"},
            outcome_status=existing.outcome_status,
            outcome_summary=existing.outcome_summary,
            outcome_details=existing.outcome_details,
            completed_at=existing.completed_at,
            result=existing.result,
        )
        upsert_workflow_run(db_path, updated)

        loaded = load_workflow_run(db_path, existing.work_item_id)

        assert loaded is not None
        assert loaded.status == NextActionType.HUMAN_UPDATE_REPO.value
        assert loaded.last_action == "run_pm"
        assert loaded.runner_name == "pm"
        assert loaded.runner_status == "completed"
        assert loaded.outcome_status == "split_required"
        assert loaded.outcome_summary == "Need to split WI-1.1.4 before coding."
        assert loaded.outcome_details["recommended_next_step"] == "update_work_item"
        assert loaded.result == {"summary": "Prepared PM handoff."}
        assert loaded.completed_at == "2026-04-06 10:00:00"


def test_parse_github_remote_supports_ssh_and_https() -> None:
    assert parse_github_remote("git@github.com:tomanizer/risk-manager.git") is not None
    assert parse_github_remote("https://github.com/tomanizer/risk-manager.git") is not None
    assert parse_github_remote("https://github.com/tomanizer/risk.manager/") is not None
    assert parse_github_remote("https://example.com/not-github.git") is None


def test_build_pull_request_snapshots_maps_live_payload() -> None:
    work_items = (
        WorkItemSnapshot(
            id="WI-1.1.3-risk-summary-history-service",
            title="WI-1.1.3",
            path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
            stage=WorkItemStage.READY,
        ),
    )
    payload: dict[str, object] = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 44,
                            "url": "https://github.com/tomanizer/risk-manager/pull/44",
                            "isDraft": False,
                            "headRefName": "codex/WI-1.1.3-risk-summary-history-service",
                            "updatedAt": "2026-04-06T10:00:00Z",
                            "title": "Implement WI-1.1.3",
                            "body": "Implements history service.",
                            "reviewDecision": "APPROVED",
                            "mergeStateStatus": "CLEAN",
                            "reviewThreads": {"nodes": [{"isResolved": True}, {"isResolved": False}]},
                            "commits": {
                                "nodes": [
                                    {
                                        "commit": {
                                            "statusCheckRollup": {
                                                "state": "SUCCESS",
                                            }
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        }
    }

    snapshots, warnings = build_pull_request_snapshots(payload, work_items)

    assert warnings == ()
    assert len(snapshots) == 1
    assert snapshots[0].work_item_id == "WI-1.1.3-risk-summary-history-service"
    assert snapshots[0].number == 44
    assert snapshots[0].unresolved_review_threads == 1
    assert snapshots[0].review_decision == "APPROVED"
    assert snapshots[0].updated_at == "2026-04-06T10:00:00Z"
    assert snapshots[0].ci_status == "SUCCESS"


def test_build_runner_execution_for_pm_uses_work_item_context() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
                linked_prd="docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md",
            ),
        )
    )

    decision = decide_next_action(snapshot)
    execution = build_runner_execution(snapshot, decision)

    assert execution is not None
    assert execution.runner_name is RunnerName.PM
    assert "WI-1.1.4-risk-summary-core-service" in execution.prompt
    assert "Linked PRD" in execution.prompt


def test_build_runner_execution_for_review_includes_pr_context() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=52,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/52",
                unresolved_review_threads=1,
            ),
        ),
    )

    decision = decide_next_action(snapshot)
    execution = build_runner_execution(snapshot, decision)

    assert decision.action is NextActionType.RUN_REVIEW
    assert execution is not None
    assert execution.runner_name is RunnerName.REVIEW
    assert "PR #52" in execution.prompt
    assert "Base ref: origin/main" in execution.prompt
    assert execution.metadata["pr_number"] == "52"


def test_build_runner_execution_for_coding_includes_base_ref() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=52,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/52",
                head_ref_name="codex/wi-1-1-4",
                ci_status="FAILURE",
            ),
        ),
    )

    decision = decide_next_action(snapshot)
    execution = build_runner_execution(snapshot, decision)

    assert decision.action is NextActionType.RUN_CODING
    assert execution is not None
    assert execution.runner_name is RunnerName.CODING
    assert "Base ref: origin/codex/wi-1-1-4" in execution.prompt


def test_build_runner_execution_preserves_decision_metadata() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=52,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/52",
                ci_status="FAILURE",
                merge_state_status="DIRTY",
                review_decision="APPROVED",
            ),
        ),
    )

    decision = decide_next_action(snapshot)
    execution = build_runner_execution(snapshot, decision)

    assert decision.action is NextActionType.RUN_CODING
    assert execution is not None
    assert execution.runner_name is RunnerName.CODING
    assert execution.metadata["ci_status"] == "FAILURE"


def test_dispatch_runner_execution_returns_prepared_result() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        )
    )

    decision = decide_next_action(snapshot)
    execution = build_runner_execution(snapshot, decision)

    assert execution is not None
    with patch.dict(os.environ, {"AGENT_RUNTIME_PM_BACKEND": "prepared"}, clear=False):
        result = dispatch_runner_execution(execution)

    assert result.runner_name is RunnerName.PM
    assert result.status is RunnerDispatchStatus.PREPARED
    assert "Prepared PM readiness handoff" in result.summary
    assert result.details["target_path"].endswith("WI-1.1.4-risk-summary-core-service.md")
    assert result.outcome_status is None


def test_completed_review_changes_requested_routes_to_coding_when_pr_is_unchanged() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=71,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/71",
                updated_at="2026-04-06T09:59:00Z",
                unresolved_review_threads=2,
                review_decision="CHANGES_REQUESTED",
            ),
        ),
        workflow_runs=(
            WorkflowRunRecord(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                run_id="review-wi-1-1-4-test-run",
                pr_number=71,
                status="run_review",
                last_action="run_review",
                runner_name="review",
                runner_status="completed",
                outcome_status="changes_requested",
                outcome_summary="Latest review triage requires a coding follow-up.",
                completed_at="2026-04-06 10:00:00",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.RUN_CODING
    assert decision.metadata["review_outcome_status"] == "changes_requested"


def test_completed_review_pass_routes_to_human_update_repo_when_pr_is_unchanged() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=71,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/71",
                updated_at="2026-04-06T09:59:00Z",
                unresolved_review_threads=1,
                review_decision="CHANGES_REQUESTED",
            ),
        ),
        workflow_runs=(
            WorkflowRunRecord(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                run_id="review-wi-1-1-4-test-run",
                pr_number=71,
                status="run_review",
                last_action="run_review",
                runner_name="review",
                runner_status="completed",
                outcome_status="pass",
                outcome_summary="No further code changes are required.",
                completed_at="2026-04-06 10:00:00",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.HUMAN_UPDATE_REPO
    assert decision.metadata["review_outcome_status"] == "pass"


def test_completed_review_pass_uses_status_specific_fallback_reason() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=71,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/71",
                updated_at="2026-04-06T09:59:00Z",
            ),
        ),
        workflow_runs=(
            WorkflowRunRecord(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                run_id="review-wi-1-1-4-test-run",
                pr_number=71,
                status="run_review",
                last_action="run_review",
                runner_name="review",
                runner_status="completed",
                outcome_status="pass",
                outcome_summary=None,
                completed_at="2026-04-06 10:00:00",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.reason == "latest review triage (pass) requires human attention"


def test_completed_review_outcome_is_ignored_after_pr_changes() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=71,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/71",
                updated_at="2026-04-06T10:01:00Z",
                unresolved_review_threads=1,
                review_decision="CHANGES_REQUESTED",
            ),
        ),
        workflow_runs=(
            WorkflowRunRecord(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                run_id="review-wi-1-1-4-test-run",
                pr_number=71,
                status="run_review",
                last_action="run_review",
                runner_name="review",
                runner_status="completed",
                outcome_status="pass",
                outcome_summary="No further code changes are required.",
                completed_at="2026-04-06 10:00:00",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.RUN_REVIEW


def test_completed_review_outcome_accepts_fractional_second_pr_timestamp() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.4-risk-summary-core-service",
                title="WI-1.1.4",
                path=Path("work_items/ready/WI-1.1.4-risk-summary-core-service.md"),
                stage=WorkItemStage.READY,
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                number=71,
                is_draft=False,
                url="https://github.com/tomanizer/risk-manager/pull/71",
                updated_at="2026-04-06T09:59:00.123Z",
            ),
        ),
        workflow_runs=(
            WorkflowRunRecord(
                work_item_id="WI-1.1.4-risk-summary-core-service",
                run_id="review-wi-1-1-4-test-run",
                pr_number=71,
                status="run_review",
                last_action="run_review",
                runner_name="review",
                runner_status="completed",
                outcome_status="pass",
                outcome_summary="No further code changes are required.",
                completed_at="2026-04-06 10:00:00",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.HUMAN_UPDATE_REPO


def test_build_pull_request_snapshots_uses_exact_work_item_matching() -> None:
    work_items = (
        WorkItemSnapshot(id="WI-1", title="WI-1", path=Path("work_items/ready/WI-1.md"), stage=WorkItemStage.READY),
        WorkItemSnapshot(id="WI-11", title="WI-11", path=Path("work_items/ready/WI-11.md"), stage=WorkItemStage.READY),
    )
    payload: dict[str, object] = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 11,
                            "url": "https://github.com/tomanizer/risk-manager/pull/11",
                            "isDraft": False,
                            "headRefName": "codex/WI-11-history",
                            "title": "Implement WI-11",
                            "body": "",
                            "reviewThreads": {"nodes": []},
                            "commits": {"nodes": []},
                        }
                    ]
                }
            }
        }
    }

    snapshots, warnings = build_pull_request_snapshots(payload, work_items)

    assert warnings == ()
    assert len(snapshots) == 1
    assert snapshots[0].work_item_id == "WI-11"


def test_build_pull_request_snapshots_skips_malformed_nodes_with_warning() -> None:
    work_items = (
        WorkItemSnapshot(
            id="WI-1.1.3-risk-summary-history-service",
            title="WI-1.1.3",
            path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
            stage=WorkItemStage.READY,
        ),
    )
    payload: dict[str, object] = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "url": "https://github.com/tomanizer/risk-manager/pull/44",
                            "isDraft": False,
                            "headRefName": "codex/WI-1.1.3-risk-summary-history-service",
                            "title": "Implement WI-1.1.3",
                            "body": "",
                            "reviewThreads": {"nodes": []},
                            "commits": {"nodes": []},
                        }
                    ]
                }
            }
        }
    }

    snapshots, warnings = build_pull_request_snapshots(payload, work_items)

    assert snapshots == ()
    assert len(warnings) == 1
    assert "malformed PR node" in warnings[0]


def test_build_pull_request_snapshots_warns_on_duplicate_work_item_prs() -> None:
    work_items = (
        WorkItemSnapshot(
            id="WI-1.1.3-risk-summary-history-service",
            title="WI-1.1.3",
            path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
            stage=WorkItemStage.READY,
        ),
    )
    payload: dict[str, object] = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 44,
                            "url": "https://github.com/tomanizer/risk-manager/pull/44",
                            "isDraft": False,
                            "headRefName": "codex/WI-1.1.3-risk-summary-history-service-a",
                            "title": "Implement WI-1.1.3",
                            "body": "",
                            "reviewThreads": {"nodes": []},
                            "commits": {"nodes": []},
                        },
                        {
                            "number": 43,
                            "url": "https://github.com/tomanizer/risk-manager/pull/43",
                            "isDraft": False,
                            "headRefName": "codex/WI-1.1.3-risk-summary-history-service-b",
                            "title": "Implement WI-1.1.3 again",
                            "body": "",
                            "reviewThreads": {"nodes": []},
                            "commits": {"nodes": []},
                        },
                    ]
                }
            }
        }
    }

    snapshots, warnings = build_pull_request_snapshots(payload, work_items)

    assert len(snapshots) == 1
    assert snapshots[0].number == 44
    assert len(warnings) == 1
    assert "multiple open PRs" in warnings[0]


def test_build_pull_request_snapshots_does_not_synthesize_new_review_comments() -> None:
    work_items = (
        WorkItemSnapshot(
            id="WI-1.1.3-risk-summary-history-service",
            title="WI-1.1.3",
            path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
            stage=WorkItemStage.READY,
        ),
    )
    payload: dict[str, object] = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 44,
                            "url": "https://github.com/tomanizer/risk-manager/pull/44",
                            "isDraft": False,
                            "headRefName": "codex/WI-1.1.3-risk-summary-history-service",
                            "title": "Implement WI-1.1.3",
                            "body": "",
                            "reviewDecision": "CHANGES_REQUESTED",
                            "reviewThreads": {"nodes": []},
                            "commits": {"nodes": []},
                        }
                    ]
                }
            }
        }
    }

    snapshots, warnings = build_pull_request_snapshots(payload, work_items)

    assert warnings == ()
    assert len(snapshots) == 1
    assert snapshots[0].has_new_review_comments is False
    assert snapshots[0].review_decision == "CHANGES_REQUESTED"


def test_extract_pull_request_page_reports_missing_page_info() -> None:
    payload: dict[str, Any] = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                }
            }
        }
    }

    nodes, warnings, page_info = _extract_pull_request_page(payload)

    assert nodes == []
    assert len(warnings) == 1
    assert "pageInfo" in warnings[0]
    assert page_info["has_next_page"] is False


def test_open_pr_with_pending_checks_reports_checks_running_before_review_wait() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-1.1.3-risk-summary-history-service",
                title="WI-1.1.3",
                path=Path("work_items/ready/WI-1.1.3-risk-summary-history-service.md"),
                stage=WorkItemStage.READY,
                dependencies=(),
            ),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-1.1.3-risk-summary-history-service",
                number=42,
                is_draft=False,
                ci_status="PENDING",
                review_decision=None,
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.WAIT_FOR_REVIEWS
    assert decision.reason == "PR checks are still running"

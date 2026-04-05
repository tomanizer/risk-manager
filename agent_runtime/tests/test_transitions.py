"""Tests for the first orchestrator transition logic."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile

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
from agent_runtime.orchestrator.simulations import build_simulation_snapshot, simulation_names
from agent_runtime.orchestrator.transitions import decide_next_action
from agent_runtime.orchestrator.work_item_registry import load_work_items
from agent_runtime.storage.sqlite import EXPECTED_WORKFLOW_RUN_COLUMNS, initialize_database


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

        actual_columns = tuple(row[1] for row in rows)
        assert actual_columns == EXPECTED_WORKFLOW_RUN_COLUMNS


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
    payload = {
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
    assert snapshots[0].ci_status == "SUCCESS"


def test_build_pull_request_snapshots_uses_exact_work_item_matching() -> None:
    work_items = (
        WorkItemSnapshot(id="WI-1", title="WI-1", path=Path("work_items/ready/WI-1.md"), stage=WorkItemStage.READY),
        WorkItemSnapshot(id="WI-11", title="WI-11", path=Path("work_items/ready/WI-11.md"), stage=WorkItemStage.READY),
    )
    payload = {
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
    payload = {
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
    payload = {
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
    payload = {
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
    payload = {
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

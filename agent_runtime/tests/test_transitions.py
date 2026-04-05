"""Tests for the first orchestrator transition logic."""

from __future__ import annotations

from pathlib import Path

from agent_runtime.orchestrator.state import (
    NextActionType,
    PullRequestSnapshot,
    RuntimeSnapshot,
    WorkItemSnapshot,
    WorkItemStage,
)
from agent_runtime.orchestrator.simulations import build_simulation_snapshot, simulation_names
from agent_runtime.orchestrator.transitions import decide_next_action


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


def test_built_in_simulation_scenarios_cover_expected_actions() -> None:
    expected_actions = {
        "ready-no-pr": NextActionType.RUN_PM,
        "blocked-dependency": NextActionType.RUN_SPEC,
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

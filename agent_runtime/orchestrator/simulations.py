"""Built-in simulation scenarios for the first orchestrator."""

from __future__ import annotations

from pathlib import Path

from .state import PullRequestSnapshot, RuntimeSnapshot, WorkItemSnapshot, WorkItemStage


def _stage_directory(stage: WorkItemStage) -> str:
    return {
        WorkItemStage.READY: "ready",
        WorkItemStage.IN_PROGRESS: "in_progress",
        WorkItemStage.BLOCKED: "blocked",
        WorkItemStage.DONE: "done",
    }[stage]


def _work_item(
    work_item_id: str,
    stage: WorkItemStage = WorkItemStage.READY,
    dependencies: tuple[str, ...] = (),
) -> WorkItemSnapshot:
    return WorkItemSnapshot(
        id=work_item_id,
        title=work_item_id,
        path=Path(f"work_items/{_stage_directory(stage)}/{work_item_id}.md"),
        stage=stage,
        dependencies=dependencies,
    )


def build_simulation_snapshot(name: str) -> RuntimeSnapshot:
    if name == "ready-no-pr":
        return RuntimeSnapshot(work_items=(_work_item("WI-1.1.3-risk-summary-history-service"),))

    if name == "blocked-dependency":
        return RuntimeSnapshot(
            work_items=(
                _work_item(
                    "WI-1.1.3-risk-summary-history-service",
                    dependencies=("WI-1.1.2-risk-summary-fixtures",),
                ),
                _work_item("WI-1.1.4-risk-summary-core-service"),
            )
        )

    if name == "draft-pr":
        return RuntimeSnapshot(
            work_items=(_work_item("WI-1.1.3-risk-summary-history-service"),),
            pull_requests=(
                PullRequestSnapshot(
                    work_item_id="WI-1.1.3-risk-summary-history-service",
                    number=42,
                    is_draft=True,
                    url="https://github.com/example/risk-manager/pull/42",
                ),
            ),
        )

    if name == "unresolved-review":
        return RuntimeSnapshot(
            work_items=(_work_item("WI-1.1.3-risk-summary-history-service"),),
            pull_requests=(
                PullRequestSnapshot(
                    work_item_id="WI-1.1.3-risk-summary-history-service",
                    number=42,
                    is_draft=True,
                    url="https://github.com/example/risk-manager/pull/42",
                    unresolved_review_threads=2,
                    has_new_review_comments=True,
                ),
            ),
        )

    if name == "ready-for-merge":
        return RuntimeSnapshot(
            work_items=(_work_item("WI-1.1.3-risk-summary-history-service"),),
            pull_requests=(
                PullRequestSnapshot(
                    work_item_id="WI-1.1.3-risk-summary-history-service",
                    number=42,
                    is_draft=False,
                    url="https://github.com/example/risk-manager/pull/42",
                    review_decision="APPROVED",
                    merge_state_status="CLEAN",
                    ci_status="SUCCESS",
                ),
            ),
        )

    if name == "failing-ci-pr":
        return RuntimeSnapshot(
            work_items=(_work_item("WI-1.1.3-risk-summary-history-service"),),
            pull_requests=(
                PullRequestSnapshot(
                    work_item_id="WI-1.1.3-risk-summary-history-service",
                    number=42,
                    is_draft=False,
                    url="https://github.com/example/risk-manager/pull/42",
                    review_decision="APPROVED",
                    merge_state_status="CLEAN",
                    ci_status="FAILURE",
                ),
            ),
        )

    if name == "noop":
        return RuntimeSnapshot(
            work_items=(
                _work_item(
                    "WI-1.1.3-risk-summary-history-service",
                    stage=WorkItemStage.BLOCKED,
                ),
            )
        )

    raise ValueError(f"unknown simulation scenario: {name}")


def simulation_names() -> tuple[str, ...]:
    return (
        "ready-no-pr",
        "blocked-dependency",
        "draft-pr",
        "unresolved-review",
        "ready-for-merge",
        "failing-ci-pr",
        "noop",
    )

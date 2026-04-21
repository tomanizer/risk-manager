"""Typed workflow state used by the runtime orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_runtime.storage.sqlite import WorkflowRunRecord


class WorkItemStage(str, Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class NextActionType(str, Enum):
    RUN_PM = "run_pm"
    RUN_SPEC = "run_spec"
    RUN_ISSUE_PLANNER = "run_issue_planner"
    RUN_CODING = "run_coding"
    WAIT_FOR_REVIEWS = "wait_for_reviews"
    WAIT_FOR_DRIFT_RESOLUTION = "wait_for_drift_resolution"
    RUN_REVIEW = "run_review"
    RUN_DRIFT_CHECK = "run_drift_check"
    HUMAN_MERGE = "human_merge"
    HUMAN_UPDATE_REPO = "human_update_repo"
    NOOP = "noop"


@dataclass(frozen=True)
class WorkItemSnapshot:
    id: str
    title: str
    path: Path
    stage: WorkItemStage
    linked_prd: str | None = None
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class PullRequestSnapshot:
    work_item_id: str
    number: int
    is_draft: bool
    url: str | None = None
    head_ref_name: str | None = None
    base_ref_name: str | None = None
    updated_at: str | None = None
    unresolved_review_threads: int = 0
    has_new_review_comments: bool = False
    review_decision: str | None = None
    merge_state_status: str | None = None
    ci_status: str | None = None


@dataclass(frozen=True)
class BacklogMaterializationSnapshot:
    source_path: str
    related_paths: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class PrdBootstrapSnapshot:
    capability_name: str
    target_prd_id: str | None
    existing_prd_path: str | None
    registry_path: str
    next_slice: str
    next_version_reason: str


@dataclass(frozen=True)
class RuntimeSnapshot:
    work_items: tuple[WorkItemSnapshot, ...]
    pull_requests: tuple[PullRequestSnapshot, ...] = ()
    workflow_runs: tuple[WorkflowRunRecord, ...] = ()
    warnings: tuple[str, ...] = ()
    drift_critical_findings: int = 0
    drift_summary_md: str | None = None
    backlog_materialization: tuple[BacklogMaterializationSnapshot, ...] = ()
    prd_bootstrap: tuple[PrdBootstrapSnapshot, ...] = ()


@dataclass(frozen=True)
class TransitionDecision:
    action: NextActionType
    work_item_id: str | None
    reason: str
    target_path: Path | None = None
    metadata: dict[str, str] = field(default_factory=dict)

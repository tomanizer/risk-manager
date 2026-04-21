"""Tests for the issue planner runner."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.state import (
    BacklogMaterializationSnapshot,
    NextActionType,
    RuntimeSnapshot,
    TransitionDecision,
    WorkItemSnapshot,
    WorkItemStage,
)
from agent_runtime.orchestrator.transitions import decide_next_action
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.issue_planner_runner import (
    IssuePlannerRunnerInput,
    build_issue_planner_prompt,
    dispatch_issue_planner_execution,
)
from agent_runtime.storage.sqlite import WorkflowRunRecord


# ---------------------------------------------------------------------------
# build_issue_planner_prompt
# ---------------------------------------------------------------------------


def test_build_issue_planner_prompt_contains_role_instruction() -> None:
    input_data = IssuePlannerRunnerInput(
        work_item_id="WI-1.1.4-risk-summary-core-service",
        split_reason="Scope is too broad for one PR.",
        work_item_path="work_items/ready/WI-1.1.4-risk-summary-core-service.md",
    )
    prompt = build_issue_planner_prompt(input_data)
    assert "Issue Planner agent" in prompt
    assert "create a fresh branch from current `main`" in prompt


def test_build_issue_planner_prompt_contains_work_item_id() -> None:
    input_data = IssuePlannerRunnerInput(
        work_item_id="WI-1.1.4-risk-summary-core-service",
        split_reason="Scope is too broad.",
        work_item_path="work_items/ready/WI-1.1.4-risk-summary-core-service.md",
    )
    prompt = build_issue_planner_prompt(input_data)
    assert "WI-1.1.4-risk-summary-core-service" in prompt


def test_build_issue_planner_prompt_contains_split_reason() -> None:
    reason = "Scope is too broad to implement and review in a single PR."
    input_data = IssuePlannerRunnerInput(
        work_item_id="WI-1.1.4-risk-summary-core-service",
        split_reason=reason,
        work_item_path="work_items/ready/WI-1.1.4-risk-summary-core-service.md",
    )
    prompt = build_issue_planner_prompt(input_data)
    assert reason in prompt


def test_build_issue_planner_prompt_includes_linked_prd_when_provided() -> None:
    input_data = IssuePlannerRunnerInput(
        work_item_id="WI-1.1.4-risk-summary-core-service",
        split_reason="Too broad.",
        work_item_path="work_items/ready/WI-1.1.4-risk-summary-core-service.md",
        linked_prd="docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md",
    )
    prompt = build_issue_planner_prompt(input_data)
    assert "docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md" in prompt


def test_build_issue_planner_prompt_instructs_narrow_slices() -> None:
    input_data = IssuePlannerRunnerInput(
        work_item_id="WI-1.1.4-risk-summary-core-service",
        split_reason="Too broad.",
        work_item_path="work_items/ready/WI-1.1.4-risk-summary-core-service.md",
    )
    prompt = build_issue_planner_prompt(input_data)
    assert "narrow" in prompt.lower()


def test_build_issue_planner_prompt_handles_backlog_materialization_context() -> None:
    input_data = IssuePlannerRunnerInput(
        work_item_id="WI-4.2.3-quant-walker-v2-implementation-prd",
        split_reason="Implementation-ready PRD follow-on WIs are missing from the live backlog.",
        work_item_path="work_items/done/WI-4.2.3-quant-walker-v2-implementation-prd.md",
        linked_prd="`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` (primary deliverable).",
        source_prd_path="docs/prds/phase-2/PRD-4.2-quant-walker-v2.md",
        missing_work_item_ids=("WI-4.2.4", "WI-4.2.5", "WI-4.2.6", "WI-4.2.7"),
    )
    prompt = build_issue_planner_prompt(input_data)
    assert "Materialize the missing follow-on work items" in prompt
    assert "Do not decompose WI-4.2.3-quant-walker-v2-implementation-prd itself again" in prompt
    assert "WI-4.2.4, WI-4.2.5, WI-4.2.6, WI-4.2.7" in prompt


def test_build_issue_planner_prompt_includes_governed_handoff_bundle_when_provided() -> None:
    prompt = build_issue_planner_prompt(
        IssuePlannerRunnerInput(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            split_reason="Scope is too broad.",
            work_item_path="work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            handoff_bundle_markdown="# Agent Handoff Bundle\n\n## Target Area\n- `agent_runtime/`",
        )
    )

    assert "## Governed Handoff Bundle" in prompt
    assert "## Target Area" in prompt


# ---------------------------------------------------------------------------
# dispatch_issue_planner_execution
# ---------------------------------------------------------------------------


def test_dispatch_issue_planner_execution_returns_prepared_status() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.ISSUE_PLANNER,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the Issue Planner agent.",
        metadata={},
    )
    result = dispatch_issue_planner_execution(execution)
    assert result.status is RunnerDispatchStatus.PREPARED


def test_dispatch_issue_planner_execution_includes_prompt_in_result() -> None:
    prompt = "Act only as the Issue Planner agent.\nDecompose WI-1.1.4."
    execution = RunnerExecution(
        runner_name=RunnerName.ISSUE_PLANNER,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt=prompt,
        metadata={},
    )
    result = dispatch_issue_planner_execution(execution)
    assert result.prompt == prompt


def test_dispatch_issue_planner_execution_summary_references_work_item() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.ISSUE_PLANNER,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the Issue Planner agent.",
        metadata={},
    )
    result = dispatch_issue_planner_execution(execution)
    assert "WI-1.1.4-risk-summary-core-service" in result.summary


def test_dispatch_issue_planner_execution_has_no_outcome_status() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.ISSUE_PLANNER,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the Issue Planner agent.",
        metadata={},
    )
    result = dispatch_issue_planner_execution(execution)
    assert result.outcome_status is None


def test_dispatch_issue_planner_execution_rejects_wrong_runner_name() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Wrong runner.",
        metadata={},
    )
    try:
        dispatch_issue_planner_execution(execution)
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "non-issue-planner" in str(exc)


# ---------------------------------------------------------------------------
# Transition: PM split_required → RUN_ISSUE_PLANNER → build_runner_execution
# ---------------------------------------------------------------------------


def test_pm_split_required_outcome_routes_to_run_issue_planner() -> None:
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
                    run_id="pm-split-test-run",
                    last_action="run_pm",
                    runner_name="pm",
                    runner_status="completed",
                    outcome_status="split_required",
                    outcome_summary="WI-1.1.4 scope needs decomposition.",
                    completed_at="2026-04-06 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_ISSUE_PLANNER
        assert decision.work_item_id == "WI-1.1.4-risk-summary-core-service"
        assert decision.metadata["pm_outcome_status"] == "split_required"
        assert "WI-1.1.4 scope needs decomposition." == decision.reason


def test_run_issue_planner_decision_builds_issue_planner_execution() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n\n## Linked PRD\n\nPRD-1.1-v2\n", encoding="utf-8")
        os.utime(work_item_path, (1_000_000_000, 1_000_000_000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                    linked_prd="PRD-1.1-v2",
                ),
            ),
        )
        decision = TransitionDecision(
            action=NextActionType.RUN_ISSUE_PLANNER,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            reason="WI-1.1.4 scope needs decomposition.",
            target_path=work_item_path,
            metadata={"pm_outcome_status": "split_required"},
        )

        execution = build_runner_execution(snapshot, decision)

        assert execution is not None
        assert execution.runner_name is RunnerName.ISSUE_PLANNER
        assert execution.work_item_id == "WI-1.1.4-risk-summary-core-service"
        assert "Issue Planner agent" in execution.prompt
        assert "PRD-1.1-v2" in execution.prompt


def test_empty_ready_queue_with_backlog_materialization_routes_to_issue_planner() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-4.2.3-quant-walker-v2-implementation-prd.md"
        work_item_path.write_text(
            "# WI-4.2.3\n\n## Linked PRD\n\n`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` (primary deliverable).\n",
            encoding="utf-8",
        )
        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-4.2.3-quant-walker-v2-implementation-prd",
                    title="WI-4.2.3",
                    path=work_item_path,
                    stage=WorkItemStage.DONE,
                    linked_prd="`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` (primary deliverable).",
                ),
            ),
            backlog_materialization=(
                BacklogMaterializationSnapshot(
                    source_path="docs/prds/phase-2/PRD-4.2-quant-walker-v2.md",
                    related_paths=("WI-4.2.4", "WI-4.2.5", "WI-4.2.6", "WI-4.2.7"),
                    message="Implementation-ready PRD follow-on WIs are missing from the live backlog.",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_ISSUE_PLANNER
        assert decision.work_item_id == "WI-4.2.3-quant-walker-v2-implementation-prd"
        assert decision.metadata["backlog_source_prd"] == "docs/prds/phase-2/PRD-4.2-quant-walker-v2.md"
        assert decision.metadata["missing_work_item_ids"] == "WI-4.2.4,WI-4.2.5,WI-4.2.6,WI-4.2.7"


def test_backlog_materialization_decision_builds_issue_planner_execution() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-4.2.3-quant-walker-v2-implementation-prd.md"
        work_item_path.write_text(
            "# WI-4.2.3\n\n## Linked PRD\n\n`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` (primary deliverable).\n",
            encoding="utf-8",
        )

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-4.2.3-quant-walker-v2-implementation-prd",
                    title="WI-4.2.3",
                    path=work_item_path,
                    stage=WorkItemStage.DONE,
                    linked_prd="`docs/prds/phase-2/PRD-4.2-quant-walker-v2.md` (primary deliverable).",
                ),
            ),
        )
        decision = TransitionDecision(
            action=NextActionType.RUN_ISSUE_PLANNER,
            work_item_id="WI-4.2.3-quant-walker-v2-implementation-prd",
            reason="Implementation-ready PRD follow-on WIs are missing from the live backlog.",
            target_path=work_item_path,
            metadata={
                "backlog_source_prd": "docs/prds/phase-2/PRD-4.2-quant-walker-v2.md",
                "missing_work_item_ids": "WI-4.2.4,WI-4.2.5,WI-4.2.6,WI-4.2.7",
            },
        )

        execution = build_runner_execution(snapshot, decision)

        assert execution is not None
        assert execution.runner_name is RunnerName.ISSUE_PLANNER
        assert "Materialize the missing follow-on work items" in execution.prompt
        assert "WI-4.2.4, WI-4.2.5, WI-4.2.6, WI-4.2.7" in execution.prompt

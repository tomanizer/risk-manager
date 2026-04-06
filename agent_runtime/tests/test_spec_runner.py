"""Tests for the spec runner."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.state import (
    NextActionType,
    RuntimeSnapshot,
    TransitionDecision,
    WorkItemSnapshot,
    WorkItemStage,
)
from agent_runtime.orchestrator.transitions import decide_next_action
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.spec_runner import (
    SpecRunnerInput,
    build_spec_prompt,
    dispatch_spec_execution,
)
from agent_runtime.storage.sqlite import WorkflowRunRecord


# ---------------------------------------------------------------------------
# build_spec_prompt
# ---------------------------------------------------------------------------


def test_build_spec_prompt_contains_role_instruction() -> None:
    input_data = SpecRunnerInput(
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        blocked_reason="PRD does not clarify which outcomes are service errors vs object statuses.",
        work_item_path="work_items/ready/WI-1.1.8-risk-delta-error-semantics.md",
    )
    prompt = build_spec_prompt(input_data)
    assert "PRD / Spec Author agent" in prompt


def test_build_spec_prompt_contains_work_item_id() -> None:
    input_data = SpecRunnerInput(
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        blocked_reason="Ambiguous error semantics in PRD.",
        work_item_path="work_items/ready/WI-1.1.8-risk-delta-error-semantics.md",
    )
    prompt = build_spec_prompt(input_data)
    assert "WI-1.1.8-risk-delta-error-semantics" in prompt


def test_build_spec_prompt_contains_blocked_reason() -> None:
    reason = "PRD does not define which statuses are object-returning vs typed service errors."
    input_data = SpecRunnerInput(
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        blocked_reason=reason,
        work_item_path="work_items/ready/WI-1.1.8-risk-delta-error-semantics.md",
    )
    prompt = build_spec_prompt(input_data)
    assert reason in prompt


def test_build_spec_prompt_includes_linked_prd_when_provided() -> None:
    input_data = SpecRunnerInput(
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        blocked_reason="Ambiguous error semantics.",
        work_item_path="work_items/ready/WI-1.1.8-risk-delta-error-semantics.md",
        linked_prd="docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md",
    )
    prompt = build_spec_prompt(input_data)
    assert "docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md" in prompt


def test_build_spec_prompt_omits_prd_line_when_none() -> None:
    input_data = SpecRunnerInput(
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        blocked_reason="Ambiguous error semantics.",
        work_item_path="work_items/ready/WI-1.1.8-risk-delta-error-semantics.md",
        linked_prd=None,
    )
    prompt = build_spec_prompt(input_data)
    assert "docs/prds/" not in prompt


def test_build_spec_prompt_instructs_not_to_push_ambiguity() -> None:
    input_data = SpecRunnerInput(
        work_item_id="WI-1.1.8",
        blocked_reason="Ambiguous error semantics.",
        work_item_path="work_items/ready/WI-1.1.8.md",
    )
    prompt = build_spec_prompt(input_data)
    assert "ambiguity" in prompt.lower()


# ---------------------------------------------------------------------------
# dispatch_spec_execution
# ---------------------------------------------------------------------------


def test_dispatch_spec_execution_returns_prepared_status() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        prompt="Act only as the PRD / Spec Author agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.8-risk-delta-error-semantics.md"},
    )
    result = dispatch_spec_execution(execution)
    assert result.status is RunnerDispatchStatus.PREPARED


def test_dispatch_spec_execution_includes_prompt_in_result() -> None:
    prompt = "Act only as the PRD / Spec Author agent.\nResolve spec gap for WI-1.1.8."
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        prompt=prompt,
        metadata={},
    )
    result = dispatch_spec_execution(execution)
    assert result.prompt == prompt


def test_dispatch_spec_execution_carries_metadata_into_details() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        prompt="Act only as the PRD / Spec Author agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.8.md", "pm_run_id": "pm-test-run-001"},
    )
    result = dispatch_spec_execution(execution)
    assert result.details["pm_run_id"] == "pm-test-run-001"
    assert result.details["target_path"] == "work_items/ready/WI-1.1.8.md"


def test_dispatch_spec_execution_has_no_outcome_status() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        prompt="Act only as the PRD / Spec Author agent.",
        metadata={},
    )
    result = dispatch_spec_execution(execution)
    assert result.outcome_status is None


def test_dispatch_spec_execution_summary_references_work_item() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        prompt="Act only as the PRD / Spec Author agent.",
        metadata={},
    )
    result = dispatch_spec_execution(execution)
    assert "WI-1.1.8-risk-delta-error-semantics" in result.summary


def test_dispatch_spec_execution_rejects_wrong_runner_name() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.8-risk-delta-error-semantics",
        prompt="Wrong runner.",
        metadata={},
    )
    try:
        dispatch_spec_execution(execution)
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "non-spec runner" in str(exc)


# ---------------------------------------------------------------------------
# Transition: PM spec_required → RUN_SPEC → build_runner_execution
# ---------------------------------------------------------------------------


def test_pm_spec_required_outcome_routes_to_run_spec() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.8-risk-delta-error-semantics.md"
        work_item_path.write_text("# WI-1.1.8\n", encoding="utf-8")
        os.utime(work_item_path, (1_000_000_000, 1_000_000_000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.8-risk-delta-error-semantics",
                    title="WI-1.1.8",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            ),
            workflow_runs=(
                WorkflowRunRecord(
                    work_item_id="WI-1.1.8-risk-delta-error-semantics",
                    status="run_pm",
                    run_id="pm-spec-test-run",
                    last_action="run_pm",
                    runner_name="pm",
                    runner_status="completed",
                    outcome_status="spec_required",
                    outcome_summary="PRD does not resolve the object-vs-error boundary.",
                    completed_at="2026-04-06 10:00:00",
                ),
            ),
        )

        decision = decide_next_action(snapshot)

        assert decision.action is NextActionType.RUN_SPEC
        assert decision.work_item_id == "WI-1.1.8-risk-delta-error-semantics"
        assert decision.metadata["pm_outcome_status"] == "spec_required"
        assert decision.metadata["pm_run_id"] == "pm-spec-test-run"


def test_run_spec_decision_builds_spec_runner_execution() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_item_path = Path(temp_dir) / "WI-1.1.8-risk-delta-error-semantics.md"
        work_item_path.write_text("# WI-1.1.8\n\n## Linked PRD\n\nPRD-1.1-v2\n", encoding="utf-8")
        os.utime(work_item_path, (1_000_000_000, 1_000_000_000))

        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.8-risk-delta-error-semantics",
                    title="WI-1.1.8",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                    linked_prd="PRD-1.1-v2",
                ),
            ),
        )
        decision = TransitionDecision(
            action=NextActionType.RUN_SPEC,
            work_item_id="WI-1.1.8-risk-delta-error-semantics",
            reason="PRD does not resolve the object-vs-error boundary.",
            target_path=work_item_path,
            metadata={"pm_outcome_status": "spec_required"},
        )

        execution = build_runner_execution(snapshot, decision)

        assert execution is not None
        assert execution.runner_name is RunnerName.SPEC
        assert execution.work_item_id == "WI-1.1.8-risk-delta-error-semantics"
        assert "PRD / Spec Author agent" in execution.prompt
        assert "PRD-1.1-v2" in execution.prompt

"""Tests for spec runner backends and PM→Spec transition routing."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from agent_runtime.config.settings import get_settings
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.prd_bootstrap import load_prd_bootstrap_candidates
from agent_runtime.orchestrator.state import (
    NextActionType,
    PrdBootstrapSnapshot,
    RuntimeSnapshot,
    TransitionDecision,
    WorkItemSnapshot,
    WorkItemStage,
)
from agent_runtime.orchestrator.transitions import decide_all_actions, decide_next_action
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.spec_runner import SpecRunnerInput, build_spec_prompt, dispatch_spec_execution
from agent_runtime.storage.sqlite import WorkflowRunRecord


# --- Spec backend dispatch tests ---


def test_dispatch_spec_execution_uses_prepared_backend_by_default() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the spec-resolution agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "prepared"}, clear=False):
        get_settings.cache_clear()
        try:
            result = dispatch_spec_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.PREPARED
    assert result.outcome_status is None
    assert "Prepared spec-resolution handoff" in result.summary


def test_dispatch_spec_execution_codex_backend_returns_completed_outcome() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the spec-resolution agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-spec-worktree",
        },
    )

    def fake_run(
        command: list[str],
        input: str,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command[:2] == ["codex", "exec"]
        assert "/tmp/runtime-spec-worktree" in command
        assert input.startswith("Act only as the spec-resolution agent.")
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "decision": "CLARIFIED",
                    "summary": "The canon gap is resolved and the work item was narrowed.",
                    "details": [{"key": "updated_artifact", "value": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("agent_runtime.runners.spec_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_spec_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "clarified"
    assert result.outcome_summary == "The canon gap is resolved and the work item was narrowed."
    assert result.outcome_details["updated_artifact"] == "work_items/ready/WI-1.1.4-risk-summary-core-service.md"
    assert result.details["spec_backend"] == "codex_exec"


def test_dispatch_spec_execution_codex_backend_rejects_non_string_details() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the spec-resolution agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-spec-worktree",
        },
    )

    def fake_run(
        command: list[str],
        input: str,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        del input, capture_output, text, check
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "decision": "CLARIFIED",
                    "summary": "The canon gap is resolved and the work item was narrowed.",
                    "details": [{"key": "updated_artifact", "value": {"bad": "shape"}}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("agent_runtime.runners.spec_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_spec_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "details in an invalid format" in result.summary


def test_dispatch_spec_execution_codex_backend_rejects_non_object_payload() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-test",
        prompt="Act only as the spec-resolution agent.",
        metadata={
            "target_path": "work_items/ready/WI-test.md",
            "worktree_path": "/tmp/runtime-spec-worktree",
        },
    )

    def fake_run(
        command: list[str],
        input: str,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        del input, capture_output, text, check
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("agent_runtime.runners.spec_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_spec_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert "parse Codex output" in result.summary


def test_dispatch_spec_execution_rejects_unknown_backend() -> None:
    """Pydantic validation rejects unknown BackendType values at config time."""
    from pydantic import ValidationError
    from agent_runtime.config.settings import AgentRuntimeConfig

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "unknown"}, clear=False):
        raised = False
        try:
            AgentRuntimeConfig()
        except ValidationError as exc:
            raised = True
            assert "spec_backend" in str(exc)
        assert raised, "Expected ValidationError for unknown BackendType"


def test_build_spec_prompt_handles_prd_bootstrap_context() -> None:
    prompt = build_spec_prompt(
        SpecRunnerInput(
            work_item_id="PRD-5.1-v2",
            blocked_reason="Registry indicates a new orchestrator PRD is required.",
            work_item_path="docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md",
            linked_prd="docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md",
            bootstrap_capability="ORCH-DAILY-RISK-INVESTIGATION",
            target_prd_id="PRD-5.1-v2",
            registry_path="docs/registry/current_state_registry.yaml",
            next_slice="Author PRD-5.1-v2 for multi-walker orchestration.",
        )
    )

    assert "Bootstrap PRD/spec drafting" in prompt
    assert "Target PRD: PRD-5.1-v2" in prompt
    assert "Current PRD: docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md" in prompt
    assert "Requested next slice: Author PRD-5.1-v2 for multi-walker orchestration." in prompt


def test_load_prd_bootstrap_candidates_returns_actionable_now_candidate_only(tmp_path: Path) -> None:
    registry_path = tmp_path / "docs" / "registry" / "current_state_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "\n".join(
            [
                "module_dashboards:",
                "  - id: DASH-1",
                "    capabilities:",
                "      - component_ref: ORCH-DAILY-RISK-INVESTIGATION",
                "        needs_new_prd_version: true",
                "        missing_prds: []",
                "        next_version_reason: Current orchestrator is bounded by PRD-5.1.",
                "        next_slice: Author PRD-5.1-v2 for multi-walker orchestration.",
                "      - component_ref: WALKER-GOVERNANCE-REPORTING",
                "        needs_new_prd_version: true",
                "        missing_prds:",
                "          - PRD-TBD-Governance-Reporting-Walker-v1",
                "        next_version_reason: Post-MVP after other implementations land.",
                "        next_slice: Post-MVP — author Governance / Reporting Walker v1 PRD after dependencies land.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    prd_path = tmp_path / "docs" / "prds" / "phase-2" / "PRD-5.1-daily-risk-investigation-orchestrator-v1.md"
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.write_text("# PRD-5.1\n\n- **PRD ID:** PRD-5.1\n", encoding="utf-8")

    candidates = load_prd_bootstrap_candidates(tmp_path)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.capability_name == "ORCH-DAILY-RISK-INVESTIGATION"
    assert candidate.target_prd_id == "PRD-5.1-v2"
    assert candidate.existing_prd_path == "docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md"


def test_load_prd_bootstrap_candidates_handles_folded_scalars_and_stops_before_prd_lineage(tmp_path: Path) -> None:
    registry_path = tmp_path / "docs" / "registry" / "current_state_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "\n".join(
            [
                "module_dashboards:",
                "  - id: DASH-1",
                "    capabilities:",
                "      - component_ref: ORCH-DAILY-RISK-INVESTIGATION",
                "        needs_new_prd_version: true",
                "        missing_prds: []",
                "        next_version_reason: >-",
                "          PRD-5.1 intentionally excludes quant routing",
                "          and richer orchestration behavior required for MVP.",
                "        next_slice: >-",
                "          Author PRD-5.1-v2 for multi-walker orchestration.",
                "      - component_ref: WALKER-QUANT",
                "        needs_new_prd_version: false",
                "        missing_prds: []",
                "        next_version_reason: >-",
                "          PRD-4.2-v2 is merged; remaining gap is implementation.",
                "        next_slice: Deliver WI-4.2.4-WI-4.2.7 per PRD-4.2-v2.",
                "    prd_lineage:",
                "      - capability: Risk Analytics",
                "        active_prd: PRD-1.1-v2",
                "        status: active",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    prd_path = tmp_path / "docs" / "prds" / "phase-2" / "PRD-5.1-daily-risk-investigation-orchestrator-v1.md"
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.write_text("# PRD-5.1\n\n- **PRD ID:** PRD-5.1\n", encoding="utf-8")

    candidates = load_prd_bootstrap_candidates(tmp_path)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.capability_name == "ORCH-DAILY-RISK-INVESTIGATION"
    assert candidate.target_prd_id == "PRD-5.1-v2"
    assert candidate.existing_prd_path == "docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md"
    assert candidate.next_version_reason == "PRD-5.1 intentionally excludes quant routing and richer orchestration behavior required for MVP."
    assert candidate.next_slice == "Author PRD-5.1-v2 for multi-walker orchestration."


# --- PM → Spec escalation transition tests ---


def _ready_item(
    work_item_id: str,
    dependencies: tuple[str, ...] = (),
) -> WorkItemSnapshot:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / f"{work_item_id}.md"
        path.write_text("# placeholder", encoding="utf-8")
        return WorkItemSnapshot(
            id=work_item_id,
            title=work_item_id,
            path=path,
            stage=WorkItemStage.READY,
            dependencies=dependencies,
        )


def test_pm_blocked_outcome_routes_to_spec() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wi_path = Path(temp_dir) / "WI-A.md"
        wi_path.write_text("# placeholder", encoding="utf-8")
        item = WorkItemSnapshot(
            id="WI-A",
            title="WI-A",
            path=wi_path,
            stage=WorkItemStage.READY,
        )
        workflow_run = WorkflowRunRecord(
            work_item_id="WI-A",
            status="run_pm",
            last_action="run_pm",
            runner_status="completed",
            outcome_status="blocked",
            outcome_summary="Canon ambiguity on lookback window default",
            completed_at="2099-12-31 23:59:59",
        )
        snapshot = RuntimeSnapshot(
            work_items=(item,),
            workflow_runs=(workflow_run,),
        )
        decision = decide_next_action(snapshot)
        assert decision.action is NextActionType.RUN_SPEC
        assert decision.work_item_id == "WI-A"
        assert "blocked" in decision.metadata.get("pm_outcome_status", "")


def test_pm_split_required_outcome_routes_to_issue_planner() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wi_path = Path(temp_dir) / "WI-B.md"
        wi_path.write_text("# placeholder", encoding="utf-8")
        item = WorkItemSnapshot(
            id="WI-B",
            title="WI-B",
            path=wi_path,
            stage=WorkItemStage.READY,
        )
        workflow_run = WorkflowRunRecord(
            work_item_id="WI-B",
            status="run_pm",
            last_action="run_pm",
            runner_status="completed",
            outcome_status="split_required",
            outcome_summary="Work item is too broad",
            completed_at="2099-12-31 23:59:59",
        )
        snapshot = RuntimeSnapshot(
            work_items=(item,),
            workflow_runs=(workflow_run,),
        )
        decision = decide_next_action(snapshot)
        assert decision.action is NextActionType.RUN_ISSUE_PLANNER


def test_completed_spec_clarified_routes_to_human_update_repo() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wi_path = Path(temp_dir) / "WI-C.md"
        wi_path.write_text("# placeholder", encoding="utf-8")
        item = WorkItemSnapshot(
            id="WI-C",
            title="WI-C",
            path=wi_path,
            stage=WorkItemStage.READY,
        )
        workflow_run = WorkflowRunRecord(
            work_item_id="WI-C",
            status="run_spec",
            last_action="run_spec",
            runner_status="completed",
            outcome_status="clarified",
            outcome_summary="Canon gap resolved",
            completed_at="2099-12-31 23:59:59",
        )
        snapshot = RuntimeSnapshot(
            work_items=(item,),
            workflow_runs=(workflow_run,),
        )
        decision = decide_next_action(snapshot)
        assert decision.action is NextActionType.HUMAN_UPDATE_REPO
        assert decision.metadata.get("spec_outcome_status") == "clarified"


def test_completed_spec_outcome_is_ignored_after_work_item_changes() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wi_path = Path(temp_dir) / "WI-D.md"
        wi_path.write_text("# placeholder", encoding="utf-8")
        item = WorkItemSnapshot(
            id="WI-D",
            title="WI-D",
            path=wi_path,
            stage=WorkItemStage.READY,
        )
        workflow_run = WorkflowRunRecord(
            work_item_id="WI-D",
            status="run_spec",
            last_action="run_spec",
            runner_status="completed",
            outcome_status="clarified",
            outcome_summary="Canon gap resolved",
            completed_at="2000-01-01 00:00:00",
        )
        snapshot = RuntimeSnapshot(
            work_items=(item,),
            workflow_runs=(workflow_run,),
        )
        decision = decide_next_action(snapshot)
        assert decision.action is NextActionType.RUN_PM


def test_decide_all_actions_includes_spec_escalation() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wi_a_path = Path(temp_dir) / "WI-A.md"
        wi_a_path.write_text("# placeholder", encoding="utf-8")
        wi_b_path = Path(temp_dir) / "WI-B.md"
        wi_b_path.write_text("# placeholder", encoding="utf-8")

        item_a = WorkItemSnapshot(
            id="WI-A",
            title="WI-A",
            path=wi_a_path,
            stage=WorkItemStage.READY,
        )
        item_b = WorkItemSnapshot(
            id="WI-B",
            title="WI-B",
            path=wi_b_path,
            stage=WorkItemStage.READY,
        )
        workflow_run = WorkflowRunRecord(
            work_item_id="WI-A",
            status="run_pm",
            last_action="run_pm",
            runner_status="completed",
            outcome_status="blocked",
            outcome_summary="Canon ambiguity",
            completed_at="2099-12-31 23:59:59",
        )
        snapshot = RuntimeSnapshot(
            work_items=(item_a, item_b),
            workflow_runs=(workflow_run,),
        )
        decisions = decide_all_actions(snapshot)
        actions_by_id = {d.work_item_id: d.action for d in decisions}
        assert actions_by_id["WI-A"] is NextActionType.RUN_SPEC
        assert actions_by_id["WI-B"] is NextActionType.RUN_PM


def test_empty_ready_queue_with_prd_bootstrap_routes_to_spec() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(),
        prd_bootstrap=(
            PrdBootstrapSnapshot(
                capability_name="ORCH-DAILY-RISK-INVESTIGATION",
                target_prd_id="PRD-5.1-v2",
                existing_prd_path="docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md",
                registry_path="docs/registry/current_state_registry.yaml",
                next_slice="Author PRD-5.1-v2 for multi-walker orchestration.",
                next_version_reason="PRD-5.1 intentionally excludes quant/time-series routing and richer orchestration behavior required for Module 1 MVP.",
            ),
        ),
    )

    decision = decide_next_action(snapshot)

    assert decision.action is NextActionType.RUN_SPEC
    assert decision.work_item_id == "PRD-5.1-v2"
    assert decision.metadata["bootstrap_mode"] == "prd_gap"
    assert decision.metadata["existing_prd_path"] == "docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md"


def test_prd_bootstrap_decision_builds_spec_execution() -> None:
    decision = TransitionDecision(
        action=NextActionType.RUN_SPEC,
        work_item_id="PRD-5.1-v2",
        reason="Registry indicates ORCH-DAILY-RISK-INVESTIGATION needs PRD-5.1-v2.",
        target_path=Path("docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md"),
        metadata={
            "bootstrap_mode": "prd_gap",
            "capability_name": "ORCH-DAILY-RISK-INVESTIGATION",
            "target_prd_id": "PRD-5.1-v2",
            "existing_prd_path": "docs/prds/phase-2/PRD-5.1-daily-risk-investigation-orchestrator-v1.md",
            "registry_path": "docs/registry/current_state_registry.yaml",
            "next_slice": "Author PRD-5.1-v2 for multi-walker orchestration.",
            "next_version_reason": "PRD-5.1 intentionally excludes quant/time-series routing and richer orchestration behavior required for Module 1 MVP.",
        },
    )

    execution = build_runner_execution(RuntimeSnapshot(work_items=()), decision)

    assert execution is not None
    assert execution.runner_name is RunnerName.SPEC
    assert "Bootstrap PRD/spec drafting for ORCH-DAILY-RISK-INVESTIGATION." in execution.prompt
    assert "Target PRD: PRD-5.1-v2" in execution.prompt


# --- Workflow run ordering tests ---


def test_latest_workflow_run_is_selected_when_multiple_exist() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wi_path = Path(temp_dir) / "WI-E.md"
        wi_path.write_text("# placeholder", encoding="utf-8")

        item = WorkItemSnapshot(
            id="WI-E",
            title="WI-E",
            path=wi_path,
            stage=WorkItemStage.READY,
        )
        old_run = WorkflowRunRecord(
            work_item_id="WI-E",
            status="run_pm",
            last_action="run_pm",
            runner_status="completed",
            outcome_status="ready",
            outcome_summary="Item is ready for coding",
            completed_at="2099-12-31 23:59:58",
            updated_at="2099-12-31 23:59:58",
        )
        new_run = WorkflowRunRecord(
            work_item_id="WI-E",
            status="run_pm",
            last_action="run_pm",
            runner_status="completed",
            outcome_status="blocked",
            outcome_summary="Canon gap found after re-review",
            completed_at="2099-12-31 23:59:59",
            updated_at="2099-12-31 23:59:59",
        )
        snapshot = RuntimeSnapshot(
            work_items=(item,),
            workflow_runs=(old_run, new_run),
        )
        decision = decide_next_action(snapshot)
        assert decision.action is NextActionType.RUN_SPEC
        assert "blocked" in decision.metadata.get("pm_outcome_status", "")

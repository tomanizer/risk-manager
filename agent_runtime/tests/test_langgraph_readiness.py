"""Tests for LangGraph readiness additions: runner protocol, prompt loading,
registry, event log, decide_all_actions, and extended dispatch status."""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from pathlib import Path

from agent_runtime.orchestrator.state import (
    NextActionType,
    PullRequestSnapshot,
    RuntimeSnapshot,
    WorkItemSnapshot,
    WorkItemStage,
)
from agent_runtime.orchestrator.transitions import decide_all_actions
from agent_runtime.runners.coding_runner import CodingRunner
from agent_runtime.runners.contracts import (
    RunnerDispatchStatus,
    RunnerExecution,
    RunnerName,
    RunnerProtocol,
)
from agent_runtime.runners.pm_runner import PMRunner
from agent_runtime.runners.prompt_loader import load_system_prompt
from agent_runtime.runners.registry import build_runner_registry
from agent_runtime.runners.review_runner import ReviewRunner
from agent_runtime.runners.spec_runner import SpecRunner
from agent_runtime.storage.sqlite import (
    EXPECTED_WORKFLOW_EVENT_COLUMNS,
    WorkflowEventRecord,
    append_workflow_event,
    initialize_database,
    load_workflow_events,
)


def _ready_item(
    work_item_id: str,
    dependencies: tuple[str, ...] = (),
) -> WorkItemSnapshot:
    return WorkItemSnapshot(
        id=work_item_id,
        title=work_item_id,
        path=Path(f"work_items/ready/{work_item_id}.md"),
        stage=WorkItemStage.READY,
        dependencies=dependencies,
    )


# --- Runner protocol tests ---


def test_all_runners_satisfy_protocol() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_root = Path(temp_dir)
        runners = [
            PMRunner(repo_root),
            SpecRunner(repo_root),
            CodingRunner(repo_root),
            ReviewRunner(repo_root),
        ]
        for runner in runners:
            assert isinstance(runner, RunnerProtocol)


def test_runner_registry_covers_all_names() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        registry = build_runner_registry(Path(temp_dir))
        assert set(registry.keys()) == set(RunnerName)


def test_runner_prepare_returns_prepared_status() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runner = PMRunner(Path(temp_dir))
        execution = RunnerExecution(
            runner_name=RunnerName.PM,
            work_item_id="WI-test",
            prompt="test prompt",
        )
        result = runner.prepare(execution)
        assert result.status is RunnerDispatchStatus.PREPARED
        assert result.work_item_id == "WI-test"


def test_runner_async_execute_delegates_to_prepare() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runner = CodingRunner(Path(temp_dir))
        execution = RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id="WI-test",
            prompt="test prompt",
        )
        result = asyncio.run(runner.execute(execution))
        assert result.status is RunnerDispatchStatus.PREPARED


# --- Prompt loader tests ---


def test_load_system_prompt_returns_governed_prompt_when_present() -> None:
    repo_root = Path(__file__).resolve()
    for _ in range(10):
        repo_root = repo_root.parent
        if (repo_root / "AGENTS.md").exists():
            break
    else:
        return

    prompt = load_system_prompt(RunnerName.PM, repo_root)
    assert "PM" in prompt
    assert len(prompt) > 100


def test_load_system_prompt_supports_all_runtime_roles() -> None:
    repo_root = Path(__file__).resolve()
    for _ in range(10):
        repo_root = repo_root.parent
        if (repo_root / "AGENTS.md").exists():
            break
    else:
        return

    for runner_name in (RunnerName.SPEC, RunnerName.ISSUE_PLANNER, RunnerName.DRIFT_MONITOR):
        prompt = load_system_prompt(runner_name, repo_root)
        assert "AGENTS.md" in prompt
        assert len(prompt) > 100


def test_load_system_prompt_falls_back_gracefully() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        prompt = load_system_prompt(RunnerName.PM, Path(temp_dir))
        assert "pm" in prompt.lower()
        assert len(prompt) < 100


def test_runner_get_system_prompt_loads_from_repo() -> None:
    repo_root = Path(__file__).resolve()
    for _ in range(10):
        repo_root = repo_root.parent
        if (repo_root / "AGENTS.md").exists():
            break
    else:
        return

    runner = ReviewRunner(repo_root)
    prompt = runner.get_system_prompt()
    assert "review" in prompt.lower()
    assert len(prompt) > 50


# --- Dispatch status lifecycle tests ---


def test_dispatch_status_has_full_lifecycle_values() -> None:
    expected = {"prepared", "running", "completed", "succeeded", "failed", "timed_out", "needs_human"}
    actual = {status.value for status in RunnerDispatchStatus}
    assert actual == expected


# --- Event log tests ---


def test_event_log_schema_is_created() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "state.db"
        initialize_database(db_path)

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("PRAGMA table_info(workflow_events)").fetchall()

        actual_columns = tuple(row[1] for row in rows)
        assert actual_columns == EXPECTED_WORKFLOW_EVENT_COLUMNS


def test_append_and_load_workflow_events() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "state.db"

        event_1 = WorkflowEventRecord(
            work_item_id="WI-1",
            action="run_pm",
            runner_name="pm",
            status="prepared",
            details={"target_path": "work_items/ready/WI-1.md"},
        )
        event_2 = WorkflowEventRecord(
            work_item_id="WI-1",
            action="run_coding",
            runner_name="coding",
            status="prepared",
        )

        id_1 = append_workflow_event(db_path, event_1)
        id_2 = append_workflow_event(db_path, event_2)
        assert id_1 > 0
        assert id_2 > id_1

        events = load_workflow_events(db_path, "WI-1")
        assert len(events) == 2
        assert events[0].action == "run_coding"
        assert events[1].action == "run_pm"


def test_load_workflow_events_respects_limit() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "state.db"
        for i in range(5):
            append_workflow_event(
                db_path,
                WorkflowEventRecord(work_item_id="WI-1", action=f"action_{i}"),
            )
        events = load_workflow_events(db_path, "WI-1", limit=3)
        assert len(events) == 3


def test_load_workflow_events_returns_empty_for_unknown_item() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "state.db"
        events = load_workflow_events(db_path, "WI-nonexistent")
        assert events == ()


# --- decide_all_actions tests ---


def test_decide_all_actions_returns_all_eligible() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            _ready_item("WI-A"),
            _ready_item("WI-B"),
            WorkItemSnapshot(
                id="WI-C",
                title="WI-C",
                path=Path("work_items/blocked/WI-C.md"),
                stage=WorkItemStage.BLOCKED,
            ),
        )
    )
    decisions = decide_all_actions(snapshot)
    assert len(decisions) == 2
    ids = {d.work_item_id for d in decisions}
    assert ids == {"WI-A", "WI-B"}


def test_decide_all_actions_respects_dependencies() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            _ready_item("WI-A", dependencies=("WI-B",)),
            _ready_item("WI-B"),
        )
    )
    decisions = decide_all_actions(snapshot)
    ids = {d.work_item_id for d in decisions}
    assert "WI-B" in ids
    assert "WI-A" not in ids


def test_decide_all_actions_returns_empty_when_nothing_runnable() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            WorkItemSnapshot(
                id="WI-done",
                title="WI-done",
                path=Path("work_items/done/WI-done.md"),
                stage=WorkItemStage.DONE,
            ),
        )
    )
    decisions = decide_all_actions(snapshot)
    assert decisions == ()


def test_decide_all_actions_mixed_pr_states() -> None:
    snapshot = RuntimeSnapshot(
        work_items=(
            _ready_item("WI-A"),
            _ready_item("WI-B"),
        ),
        pull_requests=(
            PullRequestSnapshot(
                work_item_id="WI-A",
                number=10,
                is_draft=False,
                review_decision="APPROVED",
                merge_state_status="CLEAN",
                ci_status="SUCCESS",
            ),
        ),
    )
    decisions = decide_all_actions(snapshot)
    assert len(decisions) == 2
    actions_by_id = {d.work_item_id: d.action for d in decisions}
    assert actions_by_id["WI-A"] is NextActionType.HUMAN_MERGE
    assert actions_by_id["WI-B"] is NextActionType.RUN_PM

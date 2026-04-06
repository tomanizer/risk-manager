"""Tests for spec runner backends."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.spec_runner import dispatch_spec_execution


def test_dispatch_spec_execution_uses_prepared_backend_by_default() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the spec-resolution agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "prepared"}, clear=False):
        result = dispatch_spec_execution(execution)

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
        with patch("agent_runtime.runners.spec_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_spec_execution(execution)

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
        with patch("agent_runtime.runners.spec_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_spec_execution(execution)

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "details in an invalid format" in result.summary


def test_dispatch_spec_execution_rejects_unknown_backend() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.SPEC,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the spec-resolution agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "unknown"}, clear=False):
        result = dispatch_spec_execution(execution)

    assert result.status is RunnerDispatchStatus.FAILED
    assert "Unsupported spec backend configured" in result.summary

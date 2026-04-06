"""Tests for coding runner backends."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agent_runtime.config import get_settings
from agent_runtime.runners.coding_runner import dispatch_coding_execution
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName


def test_dispatch_coding_execution_prepared_backend_when_explicitly_set() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "prepared"}, clear=False):
        get_settings.cache_clear()
        result = dispatch_coding_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.PREPARED
    assert result.outcome_status is None
    assert "Prepared coding handoff" in result.summary


def test_dispatch_coding_execution_codex_backend_returns_completed_outcome() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-coding-worktree",
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
        assert "-C" in command
        assert "/tmp/runtime-coding-worktree" in command
        assert "--output-schema" in command
        assert "-o" in command
        assert input.startswith("Act only as the coding agent.")
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "decision": "COMPLETED",
                    "summary": "Implemented the requested slice and updated tests.",
                    "details": [{"key": "changed_paths", "value": "src/foo.py,tests/test_foo.py"}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        with patch("agent_runtime.runners.coding_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_coding_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "completed"
    assert result.outcome_summary == "Implemented the requested slice and updated tests."
    assert result.outcome_details["changed_paths"] == "src/foo.py,tests/test_foo.py"
    assert result.details["backend"] == "codex_exec"


def test_dispatch_coding_execution_codex_backend_rejects_non_string_details() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-coding-worktree",
        },
    )

    def fake_run(
        command: list[str],
        input: str,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "decision": "COMPLETED",
                    "summary": "Implemented the requested slice and updated tests.",
                    "details": [{"key": "changed_paths", "value": {"bad": "shape"}}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        with patch("agent_runtime.runners.coding_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_coding_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "to be a str" in result.summary


def test_dispatch_coding_execution_codex_backend_rejects_non_object_payload() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-coding-worktree",
        },
    )

    def fake_run(
        command: list[str],
        input: str,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        with patch("agent_runtime.runners.coding_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_coding_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "could not parse Codex output" in result.summary


def test_dispatch_coding_execution_rejects_unknown_backend() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "unknown"}, clear=False):
        get_settings.cache_clear()
        with pytest.raises(ValidationError, match="coding_backend"):
            dispatch_coding_execution(execution)
    get_settings.cache_clear()

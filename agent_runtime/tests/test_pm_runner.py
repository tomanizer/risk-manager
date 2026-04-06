"""Tests for PM runner backends."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agent_runtime.config import get_settings
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.pm_runner import dispatch_pm_execution


def test_dispatch_pm_execution_uses_prepared_backend_by_default() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the PM agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "prepared"}, clear=False):
        get_settings.cache_clear()
        result = dispatch_pm_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.PREPARED
    assert result.outcome_status is None
    assert "Prepared PM readiness handoff" in result.summary


def test_dispatch_pm_execution_codex_backend_returns_completed_outcome() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the PM agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-pm-worktree",
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
        assert "/tmp/runtime-pm-worktree" in command
        assert "--output-schema" in command
        assert "-o" in command
        assert input.startswith("Act only as the PM agent.")
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "decision": "READY",
                    "summary": "The work item is implementation-ready.",
                    "details": [{"key": "reason", "value": "contracts are stable"}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        with patch("agent_runtime.runners.pm_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_pm_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "ready"
    assert result.outcome_summary == "The work item is implementation-ready."
    assert result.outcome_details["reason"] == "contracts are stable"
    assert result.details["backend"] == "codex_exec"


def test_dispatch_pm_execution_codex_backend_handles_cli_failure() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the PM agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-pm-worktree",
        },
    )

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        with patch(
            "agent_runtime.runners.pm_backend.subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["codex", "exec"],
                1,
                stdout="",
                stderr="backend failed",
            ),
        ):
            result = dispatch_pm_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "backend failed" in result.summary


def test_dispatch_pm_execution_codex_backend_rejects_non_string_details() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the PM agent.",
        metadata={
            "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
            "worktree_path": "/tmp/runtime-pm-worktree",
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
                    "decision": "READY",
                    "summary": "The work item is implementation-ready.",
                    "details": [{"key": "reason", "value": {"bad": "shape"}}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        with patch("agent_runtime.runners.pm_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_pm_execution(execution)
    get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "to be a str" in result.summary


def test_dispatch_pm_execution_rejects_unknown_backend() -> None:
    """An unrecognised backend name is rejected by pydantic at config load time."""
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the PM agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    get_settings.cache_clear()
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "unknown"}, clear=False):
        get_settings.cache_clear()
        with pytest.raises(ValidationError, match="pm_backend"):
            dispatch_pm_execution(execution)
    get_settings.cache_clear()

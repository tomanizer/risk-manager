"""Tests for coding runner backends."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from agent_runtime.config.settings import get_settings
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.coding_runner import CodingRunnerInput, build_coding_prompt, dispatch_coding_execution


def test_build_coding_prompt_includes_runtime_managed_checkout_rule() -> None:
    prompt = build_coding_prompt(
        CodingRunnerInput(
            work_item_id="WI-1.1.4-risk-summary-core-service",
            task_summary="Implement the bounded slice.",
            base_ref="origin/main",
            pr_head_branch="codex/wi-1-1-4",
        )
    )

    assert "agent_runtime" in prompt
    assert "Do not switch to `main`" in prompt
    assert "allocated worktree and checkout context as authoritative" in prompt
    assert "change branch state inside this run" in prompt
    assert "PR base ref: origin/main" in prompt
    assert "PR head branch: codex/wi-1-1-4" in prompt
    assert "git push origin HEAD:codex/wi-1-1-4" in prompt


def test_dispatch_coding_execution_prepared_backend_when_explicitly_set() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "prepared"}, clear=False):
        get_settings.cache_clear()
        try:
            result = dispatch_coding_execution(execution)
        finally:
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

    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("agent_runtime.runners.coding_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_coding_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "completed"
    assert result.outcome_summary == "Implemented the requested slice and updated tests."
    assert result.outcome_details["changed_paths"] == "src/foo.py,tests/test_foo.py"
    assert result.details["coding_backend"] == "codex_exec"


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

    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("agent_runtime.runners.coding_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_coding_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "details[0].value for 'changed_paths' must be a string" in result.summary


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

    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("agent_runtime.runners.coding_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_coding_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "could not parse Codex output" in result.summary


def test_unknown_backend_value_rejected_by_config() -> None:
    """Pydantic validation rejects unknown BackendType values at config time."""
    from pydantic import ValidationError
    from agent_runtime.config.settings import AgentRuntimeConfig

    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "unknown"}, clear=False):
        raised = False
        try:
            AgentRuntimeConfig()
        except ValidationError as exc:
            raised = True
            assert "coding_backend" in str(exc)
        assert raised, "Expected ValidationError for unknown BackendType"

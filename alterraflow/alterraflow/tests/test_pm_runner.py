"""Tests for PM runner backends."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from alterraflow.config.settings import get_settings
from alterraflow.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from alterraflow.runners.pm_runner import build_pm_prompt, dispatch_pm_execution


def test_build_pm_prompt_includes_runtime_managed_checkout_rule() -> None:
    prompt = build_pm_prompt(
        input_data=type(
            "PMInput",
            (),
            {
                "work_item_id": "WI-1.1.4-risk-summary-core-service",
                "work_item_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
                "linked_prd": "docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md",
                "handoff_bundle_markdown": None,
            },
        )()
    )

    assert "alterraflow" in prompt
    assert "Do not switch to `main`" in prompt


def test_build_pm_prompt_includes_governed_handoff_bundle_when_provided() -> None:
    prompt = build_pm_prompt(
        input_data=type(
            "PMInput",
            (),
            {
                "work_item_id": "WI-1.1.4-risk-summary-core-service",
                "work_item_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md",
                "linked_prd": None,
                "handoff_bundle_markdown": "# Agent Handoff Bundle\n\n## Acceptance Criteria\n- deterministic",
            },
        )()
    )

    assert "## Governed Handoff Bundle" in prompt
    assert "## Acceptance Criteria" in prompt


def test_dispatch_pm_execution_uses_prepared_backend_by_default() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the PM agent.",
        metadata={"target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "prepared"}, clear=False):
        get_settings.cache_clear()
        try:
            result = dispatch_pm_execution(execution)
        finally:
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

    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("alterraflow.runners.pm_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_pm_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "ready"
    assert result.outcome_summary == "The work item is implementation-ready."
    assert result.outcome_details["reason"] == "contracts are stable"
    assert result.details["pm_backend"] == "codex_exec"


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

    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch(
                "alterraflow.runners.pm_backend.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    ["codex", "exec"],
                    1,
                    stdout="",
                    stderr="backend failed",
                ),
            ):
                result = dispatch_pm_execution(execution)
        finally:
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

    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("alterraflow.runners.pm_backend.subprocess.run", side_effect=fake_run):
                result = dispatch_pm_execution(execution)
        finally:
            get_settings.cache_clear()

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "non-string detail entries" in result.summary


def test_dispatch_pm_execution_rejects_unknown_backend() -> None:
    """Pydantic validation rejects unknown BackendType values at config time."""
    from pydantic import ValidationError
    from alterraflow.config.settings import AgentRuntimeConfig

    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "unknown"}, clear=False):
        raised = False
        try:
            AgentRuntimeConfig()
        except ValidationError as exc:
            raised = True
            assert "pm_backend" in str(exc)
        assert raised, "Expected ValidationError for unknown BackendType"

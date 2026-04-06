"""Tests for review runner backends."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName
from agent_runtime.runners.review_runner import dispatch_review_execution


def test_dispatch_review_execution_uses_prepared_backend_by_default() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.REVIEW,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the review agent.",
        metadata={"pr_number": "71", "target_path": "work_items/ready/WI-1.1.4-risk-summary-core-service.md"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_REVIEW_BACKEND": "prepared"}, clear=False):
        result = dispatch_review_execution(execution)

    assert result.status is RunnerDispatchStatus.PREPARED
    assert result.outcome_status is None
    assert "Prepared review handoff" in result.summary


def test_dispatch_review_execution_codex_backend_returns_completed_outcome() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.REVIEW,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the review agent.",
        metadata={
            "pr_number": "71",
            "pr_url": "https://github.com/tomanizer/risk-manager/pull/71",
            "worktree_path": "/tmp/runtime-review-worktree",
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
        assert "/tmp/runtime-review-worktree" in command
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "decision": "CHANGES_REQUESTED",
                    "summary": "The PR needs a follow-up coding pass.",
                    "details": [{"key": "primary_issue", "value": "failing_ci"}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with patch.dict("os.environ", {"AGENT_RUNTIME_REVIEW_BACKEND": "codex_exec"}, clear=False):
        with patch("agent_runtime.runners.review_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_review_execution(execution)

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "changes_requested"
    assert result.outcome_summary == "The PR needs a follow-up coding pass."
    assert result.outcome_details["primary_issue"] == "failing_ci"
    assert result.details["review_backend"] == "codex_exec"


def test_dispatch_review_execution_codex_backend_rejects_non_string_details() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.REVIEW,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the review agent.",
        metadata={
            "pr_number": "71",
            "worktree_path": "/tmp/runtime-review-worktree",
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
                    "decision": "PASS",
                    "summary": "No further code changes are needed.",
                    "details": [{"key": "note", "value": {"bad": "shape"}}],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with patch.dict("os.environ", {"AGENT_RUNTIME_REVIEW_BACKEND": "codex_exec"}, clear=False):
        with patch("agent_runtime.runners.review_backend.subprocess.run", side_effect=fake_run):
            result = dispatch_review_execution(execution)

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "non-string detail entries" in result.summary


def test_dispatch_review_execution_rejects_unknown_backend() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.REVIEW,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the review agent.",
        metadata={"pr_number": "71"},
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_REVIEW_BACKEND": "unknown"}, clear=False):
        result = dispatch_review_execution(execution)

    assert result.status is RunnerDispatchStatus.FAILED
    assert "Unsupported review backend configured" in result.summary

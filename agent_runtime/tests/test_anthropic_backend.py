"""Tests for the Anthropic SDK reasoning backend."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName

# Import the backend module once at module-level so it stays in sys.modules.
# Individual tests patch sys.modules["anthropic"] to control what `import anthropic`
# returns inside dispatch_anthropic_reasoning at call time.
from agent_runtime.runners import anthropic_backend

_EXECUTION = RunnerExecution(
    runner_name=RunnerName.REVIEW,
    work_item_id="WI-test",
    prompt="Act only as the review agent.",
    metadata={"pr_number": "42"},
)

_ALLOWED_DECISIONS = {
    "PASS": "pass",
    "CHANGES_REQUESTED": "changes_requested",
    "BLOCKED": "blocked",
}

_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["PASS", "CHANGES_REQUESTED", "BLOCKED"]},
        "summary": {"type": "string"},
        "details": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["decision", "summary", "details"],
}

_REPO_ROOT = Path("/tmp/fake-repo")


def _make_anthropic_response(payload: dict[str, object]) -> MagicMock:
    """Build a minimal mock resembling an Anthropic messages response with a tool_use block."""
    tool_use_block = SimpleNamespace(type="tool_use", input=payload)
    response = MagicMock()
    response.content = [tool_use_block]
    return response


def _mock_settings(api_key: str = "sk-ant-test") -> MagicMock:
    settings = MagicMock()
    settings.anthropic.api_key_str = api_key
    settings.anthropic.base_url = None
    return settings


def _make_mock_anthropic() -> MagicMock:
    """Return a mock anthropic module with all exception classes set."""
    mock = MagicMock()
    mock.APIError = Exception
    mock.AuthenticationError = type("AuthenticationError", (Exception,), {})
    return mock


def test_dispatch_anthropic_reasoning_returns_completed_on_success() -> None:
    mock_anthropic = _make_mock_anthropic()
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _make_anthropic_response(
        {"decision": "PASS", "summary": "No issues found.", "details": [{"key": "note", "value": "clean"}]}
    )

    with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
        with patch("agent_runtime.config.get_settings", return_value=_mock_settings()):
            result = anthropic_backend.dispatch_anthropic_reasoning(
                _EXECUTION,
                repo_root=_REPO_ROOT,
                model="claude-sonnet-4-20250514",
                allowed_decisions=_ALLOWED_DECISIONS,
                output_schema=_OUTPUT_SCHEMA,
            )

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "pass"
    assert result.outcome_summary == "No issues found."
    assert result.outcome_details["note"] == "clean"
    assert result.details["backend"] == "anthropic_api:claude-sonnet-4-20250514"


def test_dispatch_anthropic_reasoning_returns_failed_on_api_error() -> None:
    mock_anthropic = _make_mock_anthropic()
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.side_effect = mock_anthropic.APIError("rate limit")

    with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
        with patch("agent_runtime.config.get_settings", return_value=_mock_settings()):
            result = anthropic_backend.dispatch_anthropic_reasoning(
                _EXECUTION,
                repo_root=_REPO_ROOT,
                model="claude-sonnet-4-20250514",
                allowed_decisions=_ALLOWED_DECISIONS,
                output_schema=_OUTPUT_SCHEMA,
            )

    assert result.status is RunnerDispatchStatus.FAILED
    assert "Anthropic API error" in result.summary or "rate limit" in result.summary


def test_dispatch_anthropic_reasoning_returns_failed_when_no_tool_use_block() -> None:
    mock_anthropic = _make_mock_anthropic()
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    # Response with only a text block — no tool_use
    text_block = SimpleNamespace(type="text")
    response = MagicMock()
    response.content = [text_block]
    mock_client.messages.create.return_value = response

    with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
        with patch("agent_runtime.config.get_settings", return_value=_mock_settings()):
            result = anthropic_backend.dispatch_anthropic_reasoning(
                _EXECUTION,
                repo_root=_REPO_ROOT,
                model="claude-sonnet-4-20250514",
                allowed_decisions=_ALLOWED_DECISIONS,
                output_schema=_OUTPUT_SCHEMA,
            )

    assert result.status is RunnerDispatchStatus.FAILED
    assert "no tool_use block" in result.summary


def test_dispatch_anthropic_reasoning_raises_import_error_when_not_installed() -> None:
    # Setting sys.modules["anthropic"] = None causes `import anthropic` to raise ImportError.
    with patch.dict(sys.modules, {"anthropic": None}):
        with pytest.raises(ImportError, match="risk-manager\\[sdk\\]"):
            anthropic_backend._ensure_anthropic()

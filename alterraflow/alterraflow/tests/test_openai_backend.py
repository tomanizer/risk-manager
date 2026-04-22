"""Tests for the OpenAI SDK reasoning backend."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Import the backend module once at module-level so it stays in sys.modules.
# Individual tests patch sys.modules["openai"] to control what `import openai`
# returns inside dispatch_openai_reasoning at call time.
from alterraflow.runners import openai_backend
from alterraflow.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName

_EXECUTION = RunnerExecution(
    runner_name=RunnerName.PM,
    work_item_id="WI-test",
    prompt="Act only as the PM agent.",
    metadata={"worktree_path": "/tmp/test-worktree"},
)

_ALLOWED_DECISIONS = {
    "READY": "ready",
    "BLOCKED": "blocked",
    "SPLIT_REQUIRED": "split_required",
    "SPEC_REQUIRED": "spec_required",
}

_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["READY", "BLOCKED", "SPLIT_REQUIRED", "SPEC_REQUIRED"]},
        "summary": {"type": "string"},
        "details": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["decision", "summary", "details"],
}

_REPO_ROOT = Path("/tmp/fake-repo")


def _make_openai_response(payload: dict[str, object]) -> MagicMock:
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_settings(api_key: str = "sk-test") -> MagicMock:
    settings = MagicMock()
    settings.openai.api_key_str = api_key
    settings.openai.base_url = None
    settings.openai.organization = None
    return settings


def _make_mock_openai() -> MagicMock:
    """Return a mock openai module with all exception classes set."""
    mock = MagicMock()
    mock.APIError = Exception
    mock.AuthenticationError = type("AuthenticationError", (Exception,), {})
    return mock


def test_dispatch_openai_reasoning_returns_completed_on_success() -> None:
    mock_openai = _make_mock_openai()
    mock_client = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_openai_response({"decision": "READY", "summary": "Ready to implement.", "details": []})

    with patch.dict(sys.modules, {"openai": mock_openai}):
        with patch("alterraflow.config.get_settings", return_value=_mock_settings()):
            result = openai_backend.dispatch_openai_reasoning(
                _EXECUTION,
                repo_root=_REPO_ROOT,
                model="gpt-4o",
                allowed_decisions=_ALLOWED_DECISIONS,
                output_schema=_OUTPUT_SCHEMA,
            )

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "ready"
    assert result.outcome_summary == "Ready to implement."
    assert result.details["backend"] == "openai_api:gpt-4o"


def test_dispatch_openai_reasoning_returns_failed_on_api_error() -> None:
    mock_openai = _make_mock_openai()
    mock_client = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    mock_client.chat.completions.create.side_effect = mock_openai.APIError("quota exceeded")

    with patch.dict(sys.modules, {"openai": mock_openai}):
        with patch("alterraflow.config.get_settings", return_value=_mock_settings()):
            result = openai_backend.dispatch_openai_reasoning(
                _EXECUTION,
                repo_root=_REPO_ROOT,
                model="gpt-4o",
                allowed_decisions=_ALLOWED_DECISIONS,
                output_schema=_OUTPUT_SCHEMA,
            )

    assert result.status is RunnerDispatchStatus.FAILED
    assert "OpenAI API error" in result.summary or "quota exceeded" in result.summary


def test_dispatch_openai_reasoning_returns_failed_when_api_key_missing() -> None:
    mock_openai = _make_mock_openai()

    # Build a settings mock whose openai.api_key_str raises ValueError.
    settings = MagicMock()
    type(settings.openai).api_key_str = property(lambda self: (_ for _ in ()).throw(ValueError("OPENAI_API_KEY is not configured")))

    with patch.dict(sys.modules, {"openai": mock_openai}):
        with patch("alterraflow.config.get_settings", return_value=settings):
            result = openai_backend.dispatch_openai_reasoning(
                _EXECUTION,
                repo_root=_REPO_ROOT,
                model="gpt-4o",
                allowed_decisions=_ALLOWED_DECISIONS,
                output_schema=_OUTPUT_SCHEMA,
            )

    assert result.status is RunnerDispatchStatus.FAILED
    assert "configuration error" in result.summary

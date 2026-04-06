"""Tests for the OpenAI SDK reasoning backend."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName

_REPO_ROOT = Path(__file__).parent.parent.parent


def _execution(runner_name: RunnerName = RunnerName.PM) -> RunnerExecution:
    return RunnerExecution(
        runner_name=runner_name,
        work_item_id="WI-test",
        prompt="Assess readiness for WI-test.",
        metadata={"worktree_path": "/tmp/test-worktree"},
    )


def _make_openai_mock(response_content: str) -> ModuleType:
    """Build a minimal openai module mock with a successful chat response."""
    mock_openai = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = response_content
    mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

    # Make exception classes real exceptions so except clauses work.
    mock_openai.APIError = type("APIError", (Exception,), {})
    mock_openai.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_openai.APIConnectionError = type("APIConnectionError", (Exception,), {})
    return mock_openai


@pytest.fixture()
def mock_settings_with_openai_key() -> MagicMock:
    mock = MagicMock()
    mock.openai.api_key_str = "sk-test-key"
    return mock


class TestDispatchOpenAIReasoning:
    def test_success_pm_returns_completed_outcome(self, mock_settings_with_openai_key: MagicMock) -> None:
        content = json.dumps(
            {
                "decision": "READY",
                "summary": "Item is implementation-ready.",
                "details": [{"key": "reason", "value": "contracts stable"}],
            }
        )
        mock_openai = _make_openai_mock(content)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("agent_runtime.runners.openai_backend.get_settings", return_value=mock_settings_with_openai_key):
                from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_openai_reasoning(
                    _execution(RunnerName.PM),
                    repo_root=_REPO_ROOT,
                    model="gpt-4o",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.COMPLETED
        assert result.outcome_status == "ready"
        assert result.outcome_summary == "Item is implementation-ready."
        assert result.outcome_details["reason"] == "contracts stable"
        assert result.details["pm_backend"] == "openai_api"

    def test_success_review_returns_completed_outcome(self, mock_settings_with_openai_key: MagicMock) -> None:
        content = json.dumps(
            {
                "decision": "PASS",
                "summary": "PR looks good.",
                "details": [],
            }
        )
        mock_openai = _make_openai_mock(content)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("agent_runtime.runners.openai_backend.get_settings", return_value=mock_settings_with_openai_key):
                from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.review_backend import ALLOWED_REVIEW_DECISIONS

                result = dispatch_openai_reasoning(
                    _execution(RunnerName.REVIEW),
                    repo_root=_REPO_ROOT,
                    model="gpt-4o",
                    allowed_decisions=ALLOWED_REVIEW_DECISIONS,
                    output_schema=get_output_schema(RunnerName.REVIEW),
                )

        assert result.status is RunnerDispatchStatus.COMPLETED
        assert result.outcome_status == "pass"
        assert result.details["review_backend"] == "openai_api"

    def test_returns_failed_on_missing_api_key(self) -> None:
        from unittest.mock import PropertyMock

        mock_openai = _make_openai_mock("{}")
        mock_settings = MagicMock()
        mock_openai_cfg = MagicMock()
        type(mock_openai_cfg).api_key_str = PropertyMock(side_effect=ValueError("OPENAI_API_KEY is not configured"))
        mock_settings.openai = mock_openai_cfg

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("agent_runtime.runners.openai_backend.get_settings", return_value=mock_settings):
                from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_openai_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="gpt-4o",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "not configured" in result.summary

    def test_returns_failed_on_auth_error(self, mock_settings_with_openai_key: MagicMock) -> None:
        mock_openai = _make_openai_mock("{}")
        mock_openai.OpenAI.return_value.chat.completions.create.side_effect = mock_openai.AuthenticationError(
            "invalid api key"
        )

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("agent_runtime.runners.openai_backend.get_settings", return_value=mock_settings_with_openai_key):
                from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_openai_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="gpt-4o",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "authentication failed" in result.summary

    def test_returns_failed_on_api_error(self, mock_settings_with_openai_key: MagicMock) -> None:
        mock_openai = _make_openai_mock("{}")
        mock_openai.OpenAI.return_value.chat.completions.create.side_effect = mock_openai.APIError("rate limit")

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("agent_runtime.runners.openai_backend.get_settings", return_value=mock_settings_with_openai_key):
                from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_openai_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="gpt-4o",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "API error" in result.summary

    def test_returns_failed_on_non_json_response(self, mock_settings_with_openai_key: MagicMock) -> None:
        mock_openai = _make_openai_mock("not json at all")

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("agent_runtime.runners.openai_backend.get_settings", return_value=mock_settings_with_openai_key):
                from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_openai_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="gpt-4o",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "unparseable" in result.summary

    def test_returns_failed_when_openai_not_installed(self) -> None:
        # Temporarily remove openai from sys.modules to simulate absent package.
        original = sys.modules.pop("openai", None)
        # Also remove any cached import of the backend module so the guard re-runs.
        backend_module = sys.modules.pop("agent_runtime.runners.openai_backend", None)
        try:
            from agent_runtime.runners.openai_backend import dispatch_openai_reasoning
            from agent_runtime.runners._outcome_parsing import get_output_schema
            from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

            result = dispatch_openai_reasoning(
                _execution(),
                repo_root=_REPO_ROOT,
                model="gpt-4o",
                allowed_decisions=ALLOWED_PM_DECISIONS,
                output_schema=get_output_schema(RunnerName.PM),
            )
            assert result.status is RunnerDispatchStatus.FAILED
            assert "pip install" in result.summary
        finally:
            if original is not None:
                sys.modules["openai"] = original
            if backend_module is not None:
                sys.modules["agent_runtime.runners.openai_backend"] = backend_module

"""Tests for the Anthropic SDK reasoning backend."""

from __future__ import annotations

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


def _make_anthropic_mock(tool_input: dict[str, object]) -> ModuleType:
    """Build a minimal anthropic module mock with a tool_use response."""
    mock_anthropic = MagicMock()

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = tool_input

    mock_response = MagicMock()
    mock_response.content = [tool_block]
    mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

    # Make exception classes real exceptions.
    mock_anthropic.APIError = type("APIError", (Exception,), {})
    mock_anthropic.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_anthropic.APIConnectionError = type("APIConnectionError", (Exception,), {})
    return mock_anthropic


@pytest.fixture()
def mock_settings_with_anthropic_key() -> MagicMock:
    mock = MagicMock()
    mock.anthropic.api_key_str = "sk-ant-test-key"
    return mock


class TestDispatchAnthropicReasoning:
    def test_success_pm_returns_completed_outcome(self, mock_settings_with_anthropic_key: MagicMock) -> None:
        tool_input: dict[str, object] = {
            "decision": "READY",
            "summary": "Item is implementation-ready.",
            "details": [{"key": "reason", "value": "contracts stable"}],
        }
        mock_anthropic = _make_anthropic_mock(tool_input)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "agent_runtime.runners.anthropic_backend.get_settings", return_value=mock_settings_with_anthropic_key
            ):
                from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_anthropic_reasoning(
                    _execution(RunnerName.PM),
                    repo_root=_REPO_ROOT,
                    model="claude-sonnet-4-5",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.COMPLETED
        assert result.outcome_status == "ready"
        assert result.outcome_summary == "Item is implementation-ready."
        assert result.outcome_details["reason"] == "contracts stable"
        assert result.details["pm_backend"] == "anthropic_api"

    def test_success_spec_returns_completed_outcome(self, mock_settings_with_anthropic_key: MagicMock) -> None:
        tool_input: dict[str, object] = {
            "decision": "CLARIFIED",
            "summary": "Canon gap resolved.",
            "details": [],
        }
        mock_anthropic = _make_anthropic_mock(tool_input)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "agent_runtime.runners.anthropic_backend.get_settings", return_value=mock_settings_with_anthropic_key
            ):
                from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.spec_backend import ALLOWED_SPEC_DECISIONS

                result = dispatch_anthropic_reasoning(
                    _execution(RunnerName.SPEC),
                    repo_root=_REPO_ROOT,
                    model="claude-sonnet-4-5",
                    allowed_decisions=ALLOWED_SPEC_DECISIONS,
                    output_schema=get_output_schema(RunnerName.SPEC),
                )

        assert result.status is RunnerDispatchStatus.COMPLETED
        assert result.outcome_status == "clarified"
        assert result.details["spec_backend"] == "anthropic_api"

    def test_sends_forced_tool_call(self, mock_settings_with_anthropic_key: MagicMock) -> None:
        """Verify the client is invoked with tool_choice forcing emit_outcome."""
        tool_input: dict[str, object] = {"decision": "READY", "summary": "ok", "details": []}
        mock_anthropic = _make_anthropic_mock(tool_input)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "agent_runtime.runners.anthropic_backend.get_settings", return_value=mock_settings_with_anthropic_key
            ):
                from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                dispatch_anthropic_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="claude-sonnet-4-5",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        call_kwargs = mock_anthropic.Anthropic.return_value.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "emit_outcome"}
        assert call_kwargs["tools"][0]["name"] == "emit_outcome"

    def test_returns_failed_on_missing_api_key(self) -> None:
        from unittest.mock import PropertyMock

        mock_anthropic = _make_anthropic_mock({})
        mock_settings = MagicMock()
        mock_anthropic_cfg = MagicMock()
        type(mock_anthropic_cfg).api_key_str = PropertyMock(
            side_effect=ValueError("ANTHROPIC_API_KEY is not configured")
        )
        mock_settings.anthropic = mock_anthropic_cfg

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch("agent_runtime.runners.anthropic_backend.get_settings", return_value=mock_settings):
                from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_anthropic_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="claude-sonnet-4-5",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "not configured" in result.summary

    def test_returns_failed_on_auth_error(self, mock_settings_with_anthropic_key: MagicMock) -> None:
        mock_anthropic = _make_anthropic_mock({})
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = mock_anthropic.AuthenticationError(
            "invalid key"
        )

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "agent_runtime.runners.anthropic_backend.get_settings", return_value=mock_settings_with_anthropic_key
            ):
                from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_anthropic_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="claude-sonnet-4-5",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "authentication failed" in result.summary

    def test_returns_failed_when_no_tool_use_block(self, mock_settings_with_anthropic_key: MagicMock) -> None:
        mock_anthropic = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
        mock_anthropic.APIError = type("APIError", (Exception,), {})
        mock_anthropic.AuthenticationError = type("AuthenticationError", (Exception,), {})
        mock_anthropic.APIConnectionError = type("APIConnectionError", (Exception,), {})

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "agent_runtime.runners.anthropic_backend.get_settings", return_value=mock_settings_with_anthropic_key
            ):
                from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
                from agent_runtime.runners._outcome_parsing import get_output_schema
                from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

                result = dispatch_anthropic_reasoning(
                    _execution(),
                    repo_root=_REPO_ROOT,
                    model="claude-sonnet-4-5",
                    allowed_decisions=ALLOWED_PM_DECISIONS,
                    output_schema=get_output_schema(RunnerName.PM),
                )

        assert result.status is RunnerDispatchStatus.FAILED
        assert "no tool_use block" in result.summary

    def test_returns_failed_when_anthropic_not_installed(self) -> None:
        original = sys.modules.pop("anthropic", None)
        backend_module = sys.modules.pop("agent_runtime.runners.anthropic_backend", None)
        try:
            from agent_runtime.runners.anthropic_backend import dispatch_anthropic_reasoning
            from agent_runtime.runners._outcome_parsing import get_output_schema
            from agent_runtime.runners.pm_backend import ALLOWED_PM_DECISIONS

            result = dispatch_anthropic_reasoning(
                _execution(),
                repo_root=_REPO_ROOT,
                model="claude-sonnet-4-5",
                allowed_decisions=ALLOWED_PM_DECISIONS,
                output_schema=get_output_schema(RunnerName.PM),
            )
            assert result.status is RunnerDispatchStatus.FAILED
            assert "pip install" in result.summary
        finally:
            if original is not None:
                sys.modules["anthropic"] = original
            if backend_module is not None:
                sys.modules["agent_runtime.runners.anthropic_backend"] = backend_module

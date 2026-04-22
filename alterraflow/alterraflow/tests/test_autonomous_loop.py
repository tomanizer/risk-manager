"""Tests for Iteration 1 autonomous loop features.

Covers:
- _runner_timeout_seconds helper
- _dispatch_with_timeout (timeout path)
- exception safety in the dispatch wrapper
- config-driven backend selection for all 4 runner roles
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from alterraflow.config.defaults import RuntimeDefaults
from alterraflow.config.settings import AgentRuntimeConfig, get_settings
from alterraflow.orchestrator.graph import _dispatch_with_timeout, _runner_timeout_seconds
from alterraflow.runners.contracts import (
    BackendType,
    RunnerDispatchStatus,
    RunnerExecution,
    RunnerName,
    RunnerResult,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _defaults(**overrides: object) -> RuntimeDefaults:
    kwargs = {
        "repo_root": _REPO_ROOT,
        "runner_timeout_seconds_coding": 2700,
        "runner_timeout_seconds_default": 900,
        "runner_max_retries": 2,
    }
    kwargs.update(overrides)
    return RuntimeDefaults(**kwargs)  # type: ignore[arg-type]


# --- Default backend tests (via pydantic config) ---


def test_all_roles_default_to_prepared() -> None:
    cfg = AgentRuntimeConfig()
    for role in ("pm", "review", "coding", "spec"):
        assert cfg.get_role_backend(role) == BackendType.PREPARED


def test_backend_override_via_env_var() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}, clear=False):
        get_settings.cache_clear()
        try:
            cfg = get_settings().alterraflow
            assert cfg.get_role_backend("coding") == BackendType.CODEX_EXEC
        finally:
            get_settings.cache_clear()


def test_backend_type_accepts_whitespace_and_mixed_case() -> None:
    assert BackendType("  codex_exec ") is BackendType.CODEX_EXEC
    assert BackendType("CODEX_EXEC") is BackendType.CODEX_EXEC
    assert BackendType("PREPARED") is BackendType.PREPARED


def test_alterraflow_config_normalizes_backend_env_strings() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "\tCODEX_EXEC "}, clear=False):
        cfg = AgentRuntimeConfig()
    assert cfg.pm_backend is BackendType.CODEX_EXEC


def test_get_role_model_returns_correct_model_per_backend() -> None:
    cfg = AgentRuntimeConfig()
    assert cfg.get_role_model("pm", BackendType.CODEX_EXEC) == "gpt-5"
    assert cfg.get_role_model("pm", BackendType.OPENAI_API) == "gpt-4o"
    assert cfg.get_role_model("pm", BackendType.ANTHROPIC_API) == "claude-sonnet-4-20250514"
    assert cfg.get_role_model("pm", BackendType.CURSOR_API) == "cursor-fast"
    assert cfg.get_role_model("pm", BackendType.PREPARED) == ""


def test_auto_merge_defaults_to_false() -> None:
    cfg = AgentRuntimeConfig()
    assert cfg.auto_merge is False
    assert cfg.auto_promote_wi is False


# --- _runner_timeout_seconds tests ---


def test_runner_timeout_coding_returns_coding_timeout() -> None:
    defaults = _defaults(runner_timeout_seconds_coding=2700, runner_timeout_seconds_default=900)
    assert _runner_timeout_seconds(RunnerName.CODING, defaults) == 2700


def test_runner_timeout_pm_returns_default_timeout() -> None:
    defaults = _defaults(runner_timeout_seconds_coding=2700, runner_timeout_seconds_default=900)
    assert _runner_timeout_seconds(RunnerName.PM, defaults) == 900


def test_runner_timeout_review_returns_default_timeout() -> None:
    defaults = _defaults(runner_timeout_seconds_coding=2700, runner_timeout_seconds_default=900)
    assert _runner_timeout_seconds(RunnerName.REVIEW, defaults) == 900


def test_runner_timeout_spec_returns_default_timeout() -> None:
    defaults = _defaults(runner_timeout_seconds_coding=2700, runner_timeout_seconds_default=900)
    assert _runner_timeout_seconds(RunnerName.SPEC, defaults) == 900


# --- _dispatch_with_timeout tests ---


def test_dispatch_with_timeout_returns_result_on_success() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-test-timeout",
        prompt="Act only as the PM agent.",
        metadata={},
    )
    expected = RunnerResult(
        runner_name=RunnerName.PM,
        work_item_id="WI-test-timeout",
        status=RunnerDispatchStatus.COMPLETED,
        summary="done",
        prompt="Act only as the PM agent.",
    )
    defaults = _defaults(runner_timeout_seconds_default=5)

    with patch("alterraflow.orchestrator.graph.dispatch_runner_execution", return_value=expected):
        result = _dispatch_with_timeout(execution, defaults)

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.summary == "done"


def test_dispatch_with_timeout_returns_timed_out_on_timeout() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.PM,
        work_item_id="WI-test-timeout",
        prompt="Act only as the PM agent.",
        metadata={},
    )
    defaults = _defaults(runner_timeout_seconds_default=1)

    def slow_dispatch(_exec: RunnerExecution, *, state_db_path: Path | None = None) -> RunnerResult:
        # Sleep longer than the 1s timeout but short enough that the background
        # thread clears before the test suite exits (shutdown(wait=False) abandons it).
        assert state_db_path is not None
        time.sleep(3)
        raise AssertionError("should not reach here")

    with patch("alterraflow.orchestrator.graph.dispatch_runner_execution", side_effect=slow_dispatch):
        result = _dispatch_with_timeout(execution, defaults)

    assert result.status is RunnerDispatchStatus.TIMED_OUT
    assert "timed out" in result.summary.lower()
    assert result.details.get("timeout_seconds") == "1"


def test_dispatch_with_timeout_coding_uses_longer_timeout() -> None:
    """_runner_timeout_seconds selects the coding-specific timeout for CODING runner."""
    defaults = _defaults(runner_timeout_seconds_coding=2700, runner_timeout_seconds_default=900)
    assert _runner_timeout_seconds(RunnerName.CODING, defaults) == 2700
    assert _runner_timeout_seconds(RunnerName.PM, defaults) == 900

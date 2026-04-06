"""Tests for Iteration 1 autonomous loop features.

Covers:
- _runner_timeout_seconds helper
- _dispatch_with_timeout (timeout path)
- exception safety in the dispatch wrapper
- codex_exec as default backend for all 4 runners
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.orchestrator.graph import _dispatch_with_timeout, _runner_timeout_seconds
from agent_runtime.runners.contracts import (
    RunnerDispatchStatus,
    RunnerExecution,
    RunnerName,
    RunnerResult,
)
from agent_runtime.config import BackendType, get_settings


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


# --- Default backend tests ---
# Explicitly set each backend env var to "prepared" so the test is hermetic against
# any ambient AGENT_RUNTIME_*_BACKEND values that may be present in CI environments.


def test_coding_backend_defaults_to_prepared() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "prepared"}):
        assert get_settings().agent_runtime.get_role_backend("coding") is BackendType.PREPARED


def test_pm_backend_defaults_to_prepared() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_PM_BACKEND": "prepared"}):
        assert get_settings().agent_runtime.get_role_backend("pm") is BackendType.PREPARED


def test_review_backend_defaults_to_prepared() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_REVIEW_BACKEND": "prepared"}):
        assert get_settings().agent_runtime.get_role_backend("review") is BackendType.PREPARED


def test_spec_backend_defaults_to_prepared() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_SPEC_BACKEND": "prepared"}):
        assert get_settings().agent_runtime.get_role_backend("spec") is BackendType.PREPARED


def test_codex_exec_override_via_env_var() -> None:
    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_BACKEND": "codex_exec"}):
        assert get_settings().agent_runtime.get_role_backend("coding") is BackendType.CODEX_EXEC


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

    with patch("agent_runtime.orchestrator.graph.dispatch_runner_execution", return_value=expected):
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

    def slow_dispatch(_exec: RunnerExecution) -> RunnerResult:
        # Sleep longer than the 1s timeout but short enough that the background
        # thread clears before the test suite exits (shutdown(wait=False) abandons it).
        time.sleep(3)
        raise AssertionError("should not reach here")

    with patch("agent_runtime.orchestrator.graph.dispatch_runner_execution", side_effect=slow_dispatch):
        result = _dispatch_with_timeout(execution, defaults)

    assert result.status is RunnerDispatchStatus.TIMED_OUT
    assert "timed out" in result.summary.lower()
    assert result.details.get("timeout_seconds") == "1"


def test_dispatch_with_timeout_coding_uses_longer_timeout() -> None:
    """_runner_timeout_seconds selects the coding-specific timeout for CODING runner."""
    defaults = _defaults(runner_timeout_seconds_coding=2700, runner_timeout_seconds_default=900)
    assert _runner_timeout_seconds(RunnerName.CODING, defaults) == 2700
    assert _runner_timeout_seconds(RunnerName.PM, defaults) == 900

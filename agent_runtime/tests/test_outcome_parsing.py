"""Tests for _outcome_parsing shared validation helpers."""

from __future__ import annotations

import pytest

from agent_runtime.runners._outcome_parsing import get_output_schema, parse_structured_outcome
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName

_EXECUTION = RunnerExecution(
    runner_name=RunnerName.PM,
    work_item_id="WI-test",
    prompt="Act only as the PM agent.",
    metadata={"target_path": "work_items/ready/WI-test.md"},
)

_ALLOWED_PM = {
    "READY": "ready",
    "BLOCKED": "blocked",
    "SPLIT_REQUIRED": "split_required",
    "SPEC_REQUIRED": "spec_required",
}


# --- parse_structured_outcome ---


def test_parse_structured_outcome_valid_payload_returns_completed() -> None:
    payload: dict[str, object] = {
        "decision": "READY",
        "summary": "The work item is implementation-ready.",
        "details": [{"key": "reason", "value": "contracts are stable"}],
    }
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "ready"
    assert result.outcome_summary == "The work item is implementation-ready."
    assert result.outcome_details["reason"] == "contracts are stable"
    assert result.details["backend"] == "codex_exec"
    assert result.details["target_path"] == "work_items/ready/WI-test.md"


def test_parse_structured_outcome_empty_details_list() -> None:
    payload: dict[str, object] = {"decision": "BLOCKED", "summary": "Blocked.", "details": []}
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "blocked"
    assert result.outcome_details == {}


def test_parse_structured_outcome_invalid_decision_returns_failed() -> None:
    payload: dict[str, object] = {
        "decision": "UNKNOWN_DECISION",
        "summary": "some summary",
        "details": [],
    }
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.FAILED
    assert result.outcome_status is None
    assert "UNKNOWN_DECISION" in result.summary


def test_parse_structured_outcome_decision_case_insensitive() -> None:
    payload: dict[str, object] = {"decision": "ready", "summary": "ok", "details": []}
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.COMPLETED
    assert result.outcome_status == "ready"


def test_parse_structured_outcome_non_string_decision_returns_failed() -> None:
    payload: dict[str, object] = {"decision": 42, "summary": "ok", "details": []}
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.FAILED
    assert "invalid structured response" in result.summary


def test_parse_structured_outcome_missing_summary_returns_failed() -> None:
    payload: dict[str, object] = {"decision": "READY", "details": []}
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.FAILED


def test_parse_structured_outcome_non_list_details_returns_failed() -> None:
    payload: dict[str, object] = {"decision": "READY", "summary": "ok", "details": "not-a-list"}
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.FAILED
    assert "details in an invalid format" in result.summary


def test_parse_structured_outcome_non_string_value_returns_failed() -> None:
    payload: dict[str, object] = {
        "decision": "READY",
        "summary": "ok",
        "details": [{"key": "x", "value": {"nested": "dict"}}],
    }
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "codex_exec")

    assert result.status is RunnerDispatchStatus.FAILED
    assert "to be a str" in result.summary
    assert "details[0]" in result.summary


def test_parse_structured_outcome_backend_label_in_result_details() -> None:
    payload: dict[str, object] = {"decision": "READY", "summary": "ok", "details": []}
    result = parse_structured_outcome(payload, _ALLOWED_PM, _EXECUTION, "openai_api:gpt-4o")

    assert result.details["backend"] == "openai_api:gpt-4o"


# --- get_output_schema ---


def test_get_output_schema_pm_has_correct_decisions() -> None:
    schema = get_output_schema(RunnerName.PM)
    assert isinstance(schema, dict)
    decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
    assert "READY" in decision_enum
    assert "BLOCKED" in decision_enum
    assert "SPLIT_REQUIRED" in decision_enum
    assert "SPEC_REQUIRED" in decision_enum


def test_get_output_schema_spec_has_correct_decisions() -> None:
    schema = get_output_schema(RunnerName.SPEC)
    decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
    assert "CLARIFIED" in decision_enum
    assert "BLOCKED" in decision_enum
    assert "SPLIT_REQUIRED" in decision_enum
    assert "READY" not in decision_enum


def test_get_output_schema_review_has_correct_decisions() -> None:
    schema = get_output_schema(RunnerName.REVIEW)
    decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
    assert "PASS" in decision_enum
    assert "CHANGES_REQUESTED" in decision_enum
    assert "BLOCKED" in decision_enum


def test_get_output_schema_coding_has_correct_decisions() -> None:
    schema = get_output_schema(RunnerName.CODING)
    decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
    assert "COMPLETED" in decision_enum
    assert "BLOCKED" in decision_enum
    assert "NEEDS_PM" in decision_enum


def test_get_output_schema_raises_for_unsupported_runner() -> None:
    with pytest.raises(ValueError, match="No output schema defined"):
        get_output_schema(RunnerName.DRIFT_MONITOR)

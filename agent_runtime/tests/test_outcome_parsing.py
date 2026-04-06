"""Tests for the shared structured-outcome parsing module."""

from __future__ import annotations

from agent_runtime.runners._outcome_parsing import get_output_schema, parse_structured_outcome
from agent_runtime.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName


def _execution(runner_name: RunnerName = RunnerName.PM) -> RunnerExecution:
    return RunnerExecution(
        runner_name=runner_name,
        work_item_id="WI-test",
        prompt="test prompt",
        metadata={"meta_key": "meta_val"},
    )


_PM_DECISIONS = {"READY": "ready", "BLOCKED": "blocked"}


class TestParseStructuredOutcome:
    def test_returns_completed_on_valid_payload(self) -> None:
        payload: dict[str, object] = {
            "decision": "READY",
            "summary": "Item is ready.",
            "details": [{"key": "reason", "value": "contracts stable"}],
        }
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")

        assert result.status is RunnerDispatchStatus.COMPLETED
        assert result.outcome_status == "ready"
        assert result.outcome_summary == "Item is ready."
        assert result.outcome_details == {"reason": "contracts stable"}

    def test_normalises_decision_case(self) -> None:
        payload: dict[str, object] = {"decision": "ready", "summary": "ok", "details": []}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "openai_api")
        assert result.outcome_status == "ready"

    def test_includes_metadata_and_backend_label_in_details(self) -> None:
        payload: dict[str, object] = {"decision": "READY", "summary": "ok", "details": []}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "anthropic_api")
        assert result.details["meta_key"] == "meta_val"
        assert result.details["pm_backend"] == "anthropic_api"

    def test_uses_runner_name_for_backend_key(self) -> None:
        payload: dict[str, object] = {
            "decision": "PASS",
            "summary": "ok",
            "details": [],
        }
        decisions = {"PASS": "pass"}
        result = parse_structured_outcome(payload, decisions, _execution(RunnerName.REVIEW), "codex_exec")
        assert result.details["review_backend"] == "codex_exec"

    def test_returns_failed_on_non_string_decision(self) -> None:
        payload: dict[str, object] = {"decision": 42, "summary": "ok", "details": []}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED
        assert result.outcome_status is None

    def test_returns_failed_on_missing_summary(self) -> None:
        payload: dict[str, object] = {"decision": "READY", "details": []}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED

    def test_returns_failed_on_unknown_decision(self) -> None:
        payload: dict[str, object] = {"decision": "UNKNOWN_VALUE", "summary": "ok", "details": []}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED
        assert "unsupported decision" in result.summary

    def test_returns_failed_when_details_is_not_list(self) -> None:
        payload: dict[str, object] = {"decision": "READY", "summary": "ok", "details": "bad"}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED
        assert "invalid format" in result.summary

    def test_returns_failed_when_detail_item_is_not_dict(self) -> None:
        payload: dict[str, object] = {"decision": "READY", "summary": "ok", "details": ["not_a_dict"]}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED

    def test_returns_failed_when_detail_key_is_not_string(self) -> None:
        payload: dict[str, object] = {"decision": "READY", "summary": "ok", "details": [{"key": 99, "value": "v"}]}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED
        assert "must be a string" in result.summary

    def test_returns_failed_when_detail_value_is_not_string(self) -> None:
        payload: dict[str, object] = {
            "decision": "READY",
            "summary": "ok",
            "details": [{"key": "my_key", "value": {"nested": "dict"}}],
        }
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.FAILED
        assert "details[0].value for 'my_key' must be a string" in result.summary

    def test_empty_details_list_is_valid(self) -> None:
        payload: dict[str, object] = {"decision": "BLOCKED", "summary": "blocked", "details": []}
        result = parse_structured_outcome(payload, _PM_DECISIONS, _execution(), "codex_exec")
        assert result.status is RunnerDispatchStatus.COMPLETED
        assert result.outcome_details == {}


class TestGetOutputSchema:
    def test_returns_schema_for_pm(self) -> None:
        schema = get_output_schema(RunnerName.PM)
        assert schema["type"] == "object"
        decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
        assert "READY" in decision_enum
        assert "SPEC_REQUIRED" in decision_enum

    def test_returns_schema_for_review(self) -> None:
        schema = get_output_schema(RunnerName.REVIEW)
        decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
        assert "PASS" in decision_enum
        assert "CHANGES_REQUESTED" in decision_enum

    def test_returns_schema_for_spec(self) -> None:
        schema = get_output_schema(RunnerName.SPEC)
        decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
        assert "CLARIFIED" in decision_enum

    def test_returns_schema_for_coding(self) -> None:
        schema = get_output_schema(RunnerName.CODING)
        decision_enum = schema["properties"]["decision"]["enum"]  # type: ignore[index]
        assert "COMPLETED" in decision_enum
        assert "NEEDS_PM" in decision_enum

    def test_schema_has_required_fields(self) -> None:
        schema = get_output_schema(RunnerName.PM)
        assert set(schema["required"]) == {"decision", "summary", "details"}  # type: ignore[call-overload]

    def test_raises_for_unsupported_runner(self) -> None:
        import pytest

        with pytest.raises(KeyError):
            get_output_schema(RunnerName.DRIFT_MONITOR)

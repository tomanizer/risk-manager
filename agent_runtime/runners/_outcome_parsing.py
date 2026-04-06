"""Shared structured-outcome parsing for all runner backends.

All four backend families (codex_exec, openai_api, anthropic_api, prepared)
produce the same ``{decision, summary, details}`` JSON payload.  This module
extracts the common validation and conversion logic so it is defined once and
tested once.
"""

from __future__ import annotations

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

# ---------------------------------------------------------------------------
# Output JSON-Schema registry (one schema per runner role)
# ---------------------------------------------------------------------------

_DETAILS_ITEMS_SCHEMA: dict[str, object] = {
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
    },
}


def _build_schema(decision_values: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {"type": "string", "enum": decision_values},
            "summary": {"type": "string"},
            "details": _DETAILS_ITEMS_SCHEMA,
        },
        "required": ["decision", "summary", "details"],
    }


_SCHEMAS: dict[RunnerName, dict[str, object]] = {
    RunnerName.PM: _build_schema(["READY", "BLOCKED", "SPLIT_REQUIRED", "SPEC_REQUIRED"]),
    RunnerName.REVIEW: _build_schema(["PASS", "CHANGES_REQUESTED", "BLOCKED"]),
    RunnerName.SPEC: _build_schema(["CLARIFIED", "BLOCKED", "SPLIT_REQUIRED"]),
    RunnerName.CODING: _build_schema(["COMPLETED", "BLOCKED", "NEEDS_PM"]),
}


def get_output_schema(runner_name: RunnerName) -> dict[str, object]:
    """Return the JSON Schema object for a given runner role.

    Raises ``KeyError`` if the runner does not produce a structured outcome
    (e.g. ``ISSUE_PLANNER``, ``DRIFT_MONITOR``).
    """
    return _SCHEMAS[runner_name]


# ---------------------------------------------------------------------------
# Shared outcome parser
# ---------------------------------------------------------------------------


def parse_structured_outcome(
    payload: dict[str, object],
    allowed_decisions: dict[str, str],
    execution: RunnerExecution,
    backend_label: str,
) -> RunnerResult:
    """Validate a ``{decision, summary, details}`` JSON payload and return a ``RunnerResult``.

    On success returns ``status=COMPLETED`` with ``outcome_status``,
    ``outcome_summary``, and ``outcome_details`` populated.  On any validation
    failure returns ``status=FAILED`` with a descriptive ``summary``.

    Args:
        payload: the parsed JSON dict from the backend.
        allowed_decisions: mapping of uppercase decision key → normalised value
            (e.g. ``{"READY": "ready", "BLOCKED": "blocked"}``).
        execution: the original ``RunnerExecution`` used to construct results.
        backend_label: short identifier included in error messages and the
            ``{role}_backend`` detail key (e.g. ``"codex_exec"``).
    """
    role = execution.runner_name.value

    decision_value = payload.get("decision")
    summary_value = payload.get("summary")
    details_value = payload.get("details")

    if not isinstance(decision_value, str) or not isinstance(summary_value, str):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} backend ({backend_label}) returned an invalid structured response.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    normalized_decision = allowed_decisions.get(decision_value.upper())
    if normalized_decision is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} backend ({backend_label}) returned an unsupported decision: {decision_value}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    if not isinstance(details_value, list):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} backend ({backend_label}) returned details in an invalid format.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    outcome_details: dict[str, str] = {}
    for index, item in enumerate(details_value):
        if not isinstance(item, dict):
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"{role} backend ({backend_label}) returned details in an invalid format.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )
        key = item.get("key")
        value = item.get("value")
        if not isinstance(key, str):
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"{role} backend ({backend_label}) details[{index}].key must be a string.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )
        if not isinstance(value, str):
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"{role} backend ({backend_label}) details[{index}].value for '{key}' must be a string.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )
        outcome_details[key] = value

    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary=f"Completed {role} run for {execution.work_item_id}.",
        prompt=execution.prompt,
        details={
            **execution.metadata,
            f"{role}_backend": backend_label,
        },
        outcome_status=normalized_decision,
        outcome_summary=summary_value,
        outcome_details=outcome_details,
    )

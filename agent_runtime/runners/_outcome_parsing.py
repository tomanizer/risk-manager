"""Shared structured-outcome parsing for SDK runner backends.

openai_api and anthropic_api backends produce the same
``{decision, summary, details}`` JSON payload.  This module provides:

- ``get_output_schema`` — per-role JSON schema (decision enum varies by role)
- ``parse_structured_outcome`` — validates the payload, returns a RunnerResult

Note: the codex_exec backends (``*_backend.py``) do their own parsing and
record a role-specific key in ``details`` (e.g. ``"pm_backend"``).  SDK
backends routed through ``parse_structured_outcome`` record ``details["backend"]``
instead.  Unifying these keys is tracked as a future cleanup.
"""

from __future__ import annotations

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

_DECISION_ENUMS: dict[RunnerName, list[str]] = {
    RunnerName.PM: ["READY", "BLOCKED", "SPLIT_REQUIRED", "SPEC_REQUIRED"],
    RunnerName.SPEC: ["CLARIFIED", "BLOCKED", "SPLIT_REQUIRED"],
    RunnerName.REVIEW: ["PASS", "CHANGES_REQUESTED", "BLOCKED"],
    RunnerName.CODING: ["COMPLETED", "BLOCKED", "NEEDS_PM"],
}


def get_output_schema(runner_name: RunnerName) -> dict[str, object]:
    """Return the JSON schema for the structured outcome of the given role.

    Raises:
        ValueError: if no schema is defined for ``runner_name``.
    """
    decisions = _DECISION_ENUMS.get(runner_name)
    if decisions is None:
        raise ValueError(f"No output schema defined for runner {runner_name!r}")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {
                "type": "string",
                "enum": decisions,
            },
            "summary": {
                "type": "string",
            },
            "details": {
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
            },
        },
        "required": ["decision", "summary", "details"],
    }


def _parse_details(details_value: object) -> dict[str, str]:
    """Parse and validate the ``details`` list from a backend outcome payload.

    Raises:
        ValueError: if the structure deviates from the expected schema.
    """
    if not isinstance(details_value, list):
        raise ValueError(f"Expected details to be a list of key/value objects, got {type(details_value).__name__}")
    outcome_details: dict[str, str] = {}
    for index, item in enumerate(details_value):
        if not isinstance(item, dict):
            raise ValueError(f"Expected details[{index}] to be a dict, got {type(item).__name__}")
        key = item.get("key")
        value = item.get("value")
        if not isinstance(key, str):
            raise ValueError(f"Expected details[{index}]['key'] to be a str, got {type(key).__name__}")
        if not isinstance(value, str):
            raise ValueError(f"Expected details[{index}]['value'] to be a str, got {type(value).__name__}")
        outcome_details[key] = value
    return outcome_details


def parse_structured_outcome(
    payload: dict[str, object],
    allowed_decisions: dict[str, str],
    execution: RunnerExecution,
    backend_label: str,
) -> RunnerResult:
    """Validate a ``{decision, summary, details}`` payload and return a RunnerResult.

    Returns COMPLETED on success, FAILED with a descriptive summary on any
    validation error.  Used by openai_api and anthropic_api backends.

    Args:
        payload: Already-parsed JSON object from the backend response.
        allowed_decisions: Mapping of upper-case decision string to normalised value
            (e.g. ``{"READY": "ready", "BLOCKED": "blocked"}``).
        execution: The originating RunnerExecution (for runner_name, work_item_id, prompt, metadata).
        backend_label: Human-readable label recorded in ``result.details["backend"]``
            (e.g. ``"codex_exec"``, ``"openai_api:gpt-4o"``).
    """
    decision_value = payload.get("decision")
    summary_value = payload.get("summary")
    details_value = payload.get("details")

    if not isinstance(decision_value, str) or not isinstance(summary_value, str):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{backend_label} returned an invalid structured response.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    normalized_decision = allowed_decisions.get(decision_value.upper())
    if normalized_decision is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{backend_label} returned an unsupported decision: {decision_value}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    try:
        outcome_details = _parse_details(details_value)
    except ValueError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{backend_label} returned details in an invalid format: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary=f"Completed {execution.runner_name.value} run for {execution.work_item_id}.",
        prompt=execution.prompt,
        details={
            **execution.metadata,
            "backend": backend_label,
        },
        outcome_status=normalized_decision,
        outcome_summary=summary_value,
        outcome_details=outcome_details,
    )

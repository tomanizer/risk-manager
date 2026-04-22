"""Opt-in spec runner backend integrations."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from .contracts import BackendType, RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

ALLOWED_SPEC_DECISIONS = {
    "CLARIFIED": "clarified",
    "BLOCKED": "blocked",
    "SPLIT_REQUIRED": "split_required",
}


def dispatch_prepared_spec_execution(execution: RunnerExecution) -> RunnerResult:
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared spec-resolution handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )


def dispatch_codex_spec_execution(
    execution: RunnerExecution,
    *,
    codex_bin: str = "codex",
    model: str | None = None,
) -> RunnerResult:
    if execution.runner_name is not RunnerName.SPEC:
        raise RuntimeError("Codex spec backend received a non-spec runner execution")

    worktree_path = execution.metadata.get("worktree_path")
    if not worktree_path:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="Spec backend requires an allocated worktree path before auto-execution.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    backend_prompt = _build_codex_spec_prompt(execution.prompt)

    with tempfile.TemporaryDirectory(prefix="agent-runtime-spec-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "spec_outcome_schema.json"
        output_path = temp_path / "spec_outcome.json"
        schema_path.write_text(json.dumps(_spec_output_schema(), indent=2, sort_keys=True), encoding="utf-8")

        command = [codex_bin, "exec"]
        if model:
            command.extend(["--model", model])
        command.extend(
            [
                "-C",
                worktree_path,
                "--output-schema",
                str(schema_path),
                "-o",
                str(output_path),
                "-",
            ]
        )

        try:
            completed = subprocess.run(
                command,
                input=backend_prompt,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"Spec backend failed to launch Codex CLI: {error}",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            failure_detail = stderr or stdout or f"Codex exited with status {completed.returncode}"
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"Spec backend Codex execution failed: {failure_detail}",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Codex output is not a JSON object")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"Spec backend could not parse Codex output: {error}",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )

    decision_value = payload.get("decision")
    summary_value = payload.get("summary")
    details_value = payload.get("details")
    if not isinstance(decision_value, str) or not isinstance(summary_value, str):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="Spec backend returned an invalid structured response.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    normalized_decision = ALLOWED_SPEC_DECISIONS.get(decision_value.upper())
    if normalized_decision is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Spec backend returned an unsupported decision: {decision_value}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    try:
        outcome_details = _parse_spec_details(details_value)
    except ValueError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Spec backend returned details in an invalid format: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary=f"Completed spec resolution for {execution.work_item_id}.",
        prompt=execution.prompt,
        details={
            **execution.metadata,
            "spec_backend": BackendType.CODEX_EXEC.value,
        },
        outcome_status=normalized_decision,
        outcome_summary=summary_value,
        outcome_details=outcome_details,
    )


def _build_codex_spec_prompt(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Return only a JSON object that matches the provided schema.\n"
        "Allowed decisions are CLARIFIED, BLOCKED, or SPLIT_REQUIRED.\n"
        'Represent details as a list of {"key": ..., "value": ...} objects with string values.\n'
        "Do not write product code.\n"
        "Stay in spec-resolution mode only.\n"
    )


def _spec_output_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["CLARIFIED", "BLOCKED", "SPLIT_REQUIRED"],
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


def _parse_spec_details(details_value: object) -> dict[str, str]:
    """Parse and validate the details list from a Codex spec outcome.

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

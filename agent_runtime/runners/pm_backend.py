"""Opt-in PM runner backend integrations."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

PM_BACKEND_ENV = "AGENT_RUNTIME_PM_BACKEND"
PM_CODEX_BIN_ENV = "AGENT_RUNTIME_PM_CODEX_BIN"
PM_CODEX_MODEL_ENV = "AGENT_RUNTIME_PM_CODEX_MODEL"
PM_BACKEND_PREPARED = "prepared"
PM_BACKEND_CODEX_EXEC = "codex_exec"
_ALLOWED_PM_DECISIONS = {
    "READY": "ready",
    "BLOCKED": "blocked",
    "SPLIT_REQUIRED": "split_required",
}


def get_pm_backend_name() -> str:
    return os.getenv(PM_BACKEND_ENV, PM_BACKEND_PREPARED).strip().lower() or PM_BACKEND_PREPARED


def dispatch_prepared_pm_execution(execution: RunnerExecution) -> RunnerResult:
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared PM readiness handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )


def dispatch_codex_pm_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.PM:
        raise RuntimeError("Codex PM backend received a non-PM runner execution")

    worktree_path = execution.metadata.get("worktree_path")
    if not worktree_path:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="PM backend requires an allocated worktree path before auto-execution.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    codex_bin = os.getenv(PM_CODEX_BIN_ENV, "codex")
    model = os.getenv(PM_CODEX_MODEL_ENV)
    backend_prompt = _build_codex_pm_prompt(execution.prompt)

    with tempfile.TemporaryDirectory(prefix="agent-runtime-pm-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "pm_outcome_schema.json"
        output_path = temp_path / "pm_outcome.json"
        schema_path.write_text(json.dumps(_pm_output_schema(), indent=2, sort_keys=True), encoding="utf-8")

        command = [
            codex_bin,
            "exec",
            "-C",
            worktree_path,
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
            "-",
        ]
        if model:
            command[2:2] = ["--model", model]

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
                summary=f"PM backend failed to launch Codex CLI: {error}",
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
                summary=f"PM backend Codex execution failed: {failure_detail}",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary=f"PM backend could not parse Codex output: {error}",
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
            summary="PM backend returned an invalid structured response.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    normalized_decision = _ALLOWED_PM_DECISIONS.get(decision_value.upper())
    if normalized_decision is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"PM backend returned an unsupported decision: {decision_value}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    outcome_details: dict[str, str] = {}
    if not isinstance(details_value, list):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="PM backend returned details in an invalid format.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    for item in details_value:
        if not isinstance(item, dict):
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary="PM backend returned details in an invalid format.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )
        key = item.get("key")
        value = item.get("value")
        if not isinstance(key, str) or not isinstance(value, str):
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary="PM backend returned non-string detail entries.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )
        outcome_details[key] = value
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary=f"Completed PM assessment for {execution.work_item_id}.",
        prompt=execution.prompt,
        details={
            **execution.metadata,
            "pm_backend": PM_BACKEND_CODEX_EXEC,
        },
        outcome_status=normalized_decision,
        outcome_summary=summary_value,
        outcome_details=outcome_details,
    )


def _build_codex_pm_prompt(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Return only a JSON object that matches the provided schema.\n"
        "Allowed decisions are READY, BLOCKED, or SPLIT_REQUIRED.\n"
        'Represent details as a list of {"key": ..., "value": ...} objects with string values.\n'
        "Do not write code.\n"
        "Stay in PM mode only.\n"
    )


def _pm_output_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["READY", "BLOCKED", "SPLIT_REQUIRED"],
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

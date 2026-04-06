"""Opt-in coding runner backend integrations."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

CODING_BACKEND_ENV = "AGENT_RUNTIME_CODING_BACKEND"
CODING_CODEX_BIN_ENV = "AGENT_RUNTIME_CODING_CODEX_BIN"
CODING_CODEX_MODEL_ENV = "AGENT_RUNTIME_CODING_CODEX_MODEL"
CODING_BACKEND_PREPARED = "prepared"
CODING_BACKEND_CODEX_EXEC = "codex_exec"
_ALLOWED_CODING_DECISIONS = {
    "COMPLETED": "completed",
    "BLOCKED": "blocked",
    "NEEDS_PM": "needs_pm",
}


def get_coding_backend_name() -> str:
    return os.getenv(CODING_BACKEND_ENV, CODING_BACKEND_PREPARED).strip().lower() or CODING_BACKEND_PREPARED


def dispatch_prepared_coding_execution(execution: RunnerExecution) -> RunnerResult:
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared coding handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )


def dispatch_codex_coding_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.CODING:
        raise RuntimeError("Codex coding backend received a non-coding runner execution")

    worktree_path = execution.metadata.get("worktree_path")
    if not worktree_path:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="Coding backend requires an allocated worktree path before auto-execution.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    codex_bin = os.getenv(CODING_CODEX_BIN_ENV, "codex")
    model = os.getenv(CODING_CODEX_MODEL_ENV)
    backend_prompt = _build_codex_coding_prompt(execution.prompt)

    with tempfile.TemporaryDirectory(prefix="agent-runtime-coding-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "coding_outcome_schema.json"
        output_path = temp_path / "coding_outcome.json"
        schema_path.write_text(json.dumps(_coding_output_schema(), indent=2, sort_keys=True), encoding="utf-8")

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
                summary=f"Coding backend failed to launch Codex CLI: {error}",
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
                summary=f"Coding backend Codex execution failed: {failure_detail}",
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
                summary=f"Coding backend could not parse Codex output: {error}",
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
            summary="Coding backend returned an invalid structured response.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    normalized_decision = _ALLOWED_CODING_DECISIONS.get(decision_value.upper())
    if normalized_decision is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Coding backend returned an unsupported decision: {decision_value}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    outcome_details: dict[str, str] = {}
    if not isinstance(details_value, list):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="Coding backend returned details in an invalid format.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    for item in details_value:
        if not isinstance(item, dict):
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.FAILED,
                summary="Coding backend returned details in an invalid format.",
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
                summary="Coding backend returned non-string detail entries.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
            )
        outcome_details[key] = value

    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary=f"Completed coding run for {execution.work_item_id}.",
        prompt=execution.prompt,
        details={
            **execution.metadata,
            "coding_backend": CODING_BACKEND_CODEX_EXEC,
        },
        outcome_status=normalized_decision,
        outcome_summary=summary_value,
        outcome_details=outcome_details,
    )


def _build_codex_coding_prompt(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Implement the requested slice directly in the allocated worktree when appropriate.\n"
        "Return only a JSON object that matches the provided schema.\n"
        "Allowed decisions are COMPLETED, BLOCKED, or NEEDS_PM.\n"
        'Represent details as a list of {"key": ..., "value": ...} objects with string values.\n'
        "Keep the written summary concise and outcome-focused.\n"
    )


def _coding_output_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["COMPLETED", "BLOCKED", "NEEDS_PM"],
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

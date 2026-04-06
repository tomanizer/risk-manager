"""Opt-in coding runner backend integrations."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from ._outcome_parsing import get_output_schema, parse_structured_outcome
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

ALLOWED_CODING_DECISIONS: dict[str, str] = {
    "COMPLETED": "completed",
    "BLOCKED": "blocked",
    "NEEDS_PM": "needs_pm",
}


def dispatch_prepared_coding_execution(execution: RunnerExecution) -> RunnerResult:
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary=f"Prepared coding handoff for {execution.work_item_id}.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )


def dispatch_codex_coding_execution(
    execution: RunnerExecution,
    codex_bin: str = "codex",
    model: str | None = None,
) -> RunnerResult:
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

    backend_prompt = _build_codex_coding_prompt(execution.prompt)

    with tempfile.TemporaryDirectory(prefix="agent-runtime-coding-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "coding_outcome_schema.json"
        output_path = temp_path / "coding_outcome.json"
        schema_path.write_text(
            json.dumps(get_output_schema(RunnerName.CODING), indent=2, sort_keys=True), encoding="utf-8"
        )

        command = [codex_bin, "exec"]
        if model:
            command.extend(["--model", model])
        command.extend(["-C", worktree_path, "--output-schema", str(schema_path), "-o", str(output_path), "-"])

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

    return parse_structured_outcome(payload, ALLOWED_CODING_DECISIONS, execution, "codex_exec")


def _build_codex_coding_prompt(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Implement the requested slice directly in the allocated worktree when appropriate.\n"
        "Return only a JSON object that matches the provided schema.\n"
        "Allowed decisions are COMPLETED, BLOCKED, or NEEDS_PM.\n"
        'Represent details as a list of {"key": ..., "value": ...} objects with string values.\n'
        "Keep the written summary concise and outcome-focused.\n"
    )

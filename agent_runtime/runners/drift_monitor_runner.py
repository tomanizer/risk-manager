"""Drift Monitor runner — dispatches the Drift Monitor agent or drift suite."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult

DRIFT_MONITOR_BACKEND_ENV = "AGENT_RUNTIME_DRIFT_MONITOR_BACKEND"
DRIFT_MONITOR_BACKEND_PREPARED = "prepared"
DRIFT_MONITOR_BACKEND_SCRIPT = "script"


@dataclass(frozen=True)
class DriftMonitorRunnerInput:
    repo_root: str
    focus_area: str | None = None


def build_drift_monitor_prompt(input_data: DriftMonitorRunnerInput) -> str:
    prompt = (
        "Act only as the Drift Monitor agent.\n"
        "Work from current `main`.\n"
        "Read:\n"
        "- AGENTS.md\n"
        "- prompts/agents/drift_monitor_agent_instruction.md\n"
        "\n"
        "Run deterministic scanners first:\n"
        "  python scripts/drift/run_all.py --fail-on-findings\n"
        "\n"
        "Then audit for:\n"
        "- instruction surface gaps between prompts/agents/ and .github/agents/\n"
        "- README inventory drift\n"
        "- broken or stale cross-references\n"
        "- dependency hygiene issues\n"
        "- canon lineage violations\n"
        "- registry alignment issues\n"
        "\n"
    )
    if input_data.focus_area:
        prompt += f"Focus area: {input_data.focus_area}\n\n"
    prompt += (
        "Return:\n"
        "1. deterministic scanner findings (net-new vs baselined)\n"
        "2. manual audit findings\n"
        "3. recommended fixes with exact file paths\n"
        "4. items that require human escalation\n"
        "5. overall verdict: CLEAN or FINDINGS\n"
    )
    return prompt


def _get_backend() -> str:
    import os
    return os.getenv(DRIFT_MONITOR_BACKEND_ENV, DRIFT_MONITOR_BACKEND_PREPARED).strip().lower() or DRIFT_MONITOR_BACKEND_PREPARED


def dispatch_drift_monitor_execution(execution: RunnerExecution) -> RunnerResult:
    if execution.runner_name is not RunnerName.DRIFT_MONITOR:
        raise RuntimeError("Drift Monitor dispatch received a non-drift-monitor runner execution")

    backend = _get_backend()

    if backend == DRIFT_MONITOR_BACKEND_SCRIPT:
        if execution.metadata.get("governance_already_run") == "true":
            return RunnerResult(
                runner_name=execution.runner_name,
                work_item_id=execution.work_item_id,
                status=RunnerDispatchStatus.COMPLETED,
                summary="Drift check already completed by governance pre-step; net-new findings exist.",
                prompt=execution.prompt,
                details=dict(execution.metadata),
                outcome_status="findings",
                outcome_summary=execution.metadata.get("reason", "Drift findings detected by governance pre-step."),
            )
        return _dispatch_script(execution)

    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.PREPARED,
        summary="Prepared drift-monitor handoff. Run the prompt against the Drift Monitor agent.",
        prompt=execution.prompt,
        details=dict(execution.metadata),
    )


def _dispatch_script(execution: RunnerExecution) -> RunnerResult:
    """Run the drift suite script directly and return findings as the outcome."""
    repo_root = execution.metadata.get("repo_root", ".")
    script_path = Path(repo_root) / "scripts" / "drift" / "run_all.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--fail-on-findings"],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Drift monitor script failed to launch: {error}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    if result.returncode == 0:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.COMPLETED,
            summary="Drift suite passed: no net-new findings.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
            outcome_status="clean",
            outcome_summary="All deterministic drift scanners passed with no net-new findings.",
        )

    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or f"script exited with status {result.returncode}"
    return RunnerResult(
        runner_name=execution.runner_name,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary=f"Drift suite found net-new findings: {detail[:200]}",
        prompt=execution.prompt,
        details=dict(execution.metadata),
        outcome_status="findings",
        outcome_summary=detail[:500],
    )

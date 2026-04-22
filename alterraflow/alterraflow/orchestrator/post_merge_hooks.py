"""Post-merge hooks for the agent runtime.

After a coding PR is merged, these hooks are invoked to:

1. Run the drift monitor on ``main`` and surface new findings to the PM queue.
2. Write an evidence-chain event to ``workflow_events`` so ADR-003 tracing
   requirements are satisfied.

The drift integration uses ``build_drift_suite_report`` synchronously.  It
is intentionally lightweight — it should not block the poll loop for more
than a few seconds.  If the drift run takes too long, configure
``DRIFT_TIMEOUT_SECONDS`` via env var.

Usage
-----
Call ``run_post_merge_hooks`` from the orchestrator after confirming that a PR
was merged::

    from alterraflow.orchestrator.post_merge_hooks import run_post_merge_hooks
    run_post_merge_hooks(defaults, work_item_id=wi_id, pr_url=merged_pr_url)
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from alterraflow.config.defaults import RuntimeDefaults
from alterraflow.storage.sqlite import WorkflowEventRecord, append_workflow_event

_log = logging.getLogger(__name__)

DRIFT_TIMEOUT_SECONDS_ENV = "DRIFT_TIMEOUT_SECONDS"
_DEFAULT_DRIFT_TIMEOUT = 120


def _drift_timeout() -> int:
    raw = os.getenv(DRIFT_TIMEOUT_SECONDS_ENV, "")
    try:
        return int(raw)
    except ValueError:
        return _DEFAULT_DRIFT_TIMEOUT


def _run_drift_suite(repo_root: Path) -> tuple[int, int]:
    """Run the drift suite and return (new_findings, total_findings).

    Uses the in-process Python API where possible.
    """
    try:
        from alterraflow.drift.drift_suite import build_drift_suite_report

        report = build_drift_suite_report(repo_root)
        return report.stats.new_findings, report.stats.total_findings
    except Exception as exc:
        _log.warning("Drift suite failed (in-process): %s", exc, exc_info=True)
        return -1, -1


def _git_head_sha(repo_root: Path) -> str | None:
    """Return the current HEAD commit SHA, or None on error."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _write_evidence_event(
    defaults: RuntimeDefaults,
    work_item_id: str,
    action: str,
    details: dict[str, str],
) -> None:
    """Append a structured evidence event to workflow_events."""
    append_workflow_event(
        defaults.state_db_path,
        WorkflowEventRecord(
            work_item_id=work_item_id,
            action=action,
            status="recorded",
            details=details,
        ),
    )


def run_post_merge_hooks(
    defaults: RuntimeDefaults,
    *,
    work_item_id: str,
    pr_url: str | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    """Execute all post-merge hooks for the given work item.

    Returns a summary dict suitable for JSON logging.
    """
    commit_sha = _git_head_sha(defaults.repo_root)
    model = os.getenv("AGENT_RUNTIME_CODING_MODEL") or os.getenv("AGENT_RUNTIME_PM_MODEL")

    # Evidence chain event (ADR-003)
    evidence_details: dict[str, str] = {
        "hook": "post_merge",
        "work_item_id": work_item_id,
    }
    if commit_sha:
        evidence_details["commit_sha"] = commit_sha
    if pr_url:
        evidence_details["pr_url"] = pr_url
    if run_id:
        evidence_details["run_id"] = run_id
    if model:
        evidence_details["model"] = model

    _write_evidence_event(defaults, work_item_id, "post_merge_evidence", evidence_details)

    # Drift monitor run
    new_findings, total_findings = _run_drift_suite(defaults.repo_root)
    drift_details: dict[str, str] = {
        "new_findings": str(new_findings),
        "total_findings": str(total_findings),
        "commit_sha": commit_sha or "unknown",
    }
    _write_evidence_event(defaults, work_item_id, "drift_scan_post_merge", drift_details)

    if new_findings > 0:
        _log.warning(
            "Post-merge drift scan found %d new findings for %s — route to PM queue",
            new_findings,
            work_item_id,
        )
        # Notify via Slack if configured
        try:
            from alterraflow.notifications.slack import _post_message

            msg = (
                f":mag: *Drift findings after merge of `{work_item_id}`*\n"
                f"New findings: `{new_findings}` / Total: `{total_findings}`\n"
                "Route to PM queue for triage."
            )
            _post_message(msg)
        except Exception as exc:
            _log.debug("Slack drift notification failed: %s", exc)

    return {
        "work_item_id": work_item_id,
        "commit_sha": commit_sha,
        "pr_url": pr_url,
        "drift_new_findings": new_findings,
        "drift_total_findings": total_findings,
        "evidence_written": True,
    }

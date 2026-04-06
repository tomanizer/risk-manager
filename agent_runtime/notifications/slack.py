"""Slack notification helpers for the agent runtime.

Notifications are sent via an Incoming Webhook URL configured through the
``SLACK_WEBHOOK_URL`` environment variable.  When the variable is not set the
module degrades gracefully — all calls are no-ops and a single debug-level
log message is emitted so operators know why they received no notification.

Usage
-----
Set ``SLACK_WEBHOOK_URL`` to a Slack Incoming Webhook URL:

    export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

Optionally, restrict digest notifications to a specific channel by setting
``SLACK_NOTIFY_CHANNEL`` (e.g. ``#agent-runtime``).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_runtime.telemetry import get_logger

_log = get_logger(__name__)

SLACK_WEBHOOK_URL_ENV = "SLACK_WEBHOOK_URL"
SLACK_NOTIFY_CHANNEL_ENV = "SLACK_NOTIFY_CHANNEL"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _webhook_url() -> str | None:
    return os.getenv(SLACK_WEBHOOK_URL_ENV)


def _post_message(text: str, blocks: list[dict[str, object]] | None = None) -> bool:
    """POST a message to the configured Slack webhook.

    Returns True on success, False on any error.  Never raises.
    """
    url = _webhook_url()
    if not url:
        _log.debug("slack_webhook_not_configured")
        return False

    payload: dict[str, object] = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    channel = os.getenv(SLACK_NOTIFY_CHANNEL_ENV)
    if channel:
        payload["channel"] = channel

    raw = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=raw,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                _log.warning("slack_webhook_unexpected_status", status=response.status)
                return False
        return True
    except urllib.error.URLError as exc:
        _log.warning("slack_notification_failed", error=str(exc))
        return False


def _mrkdwn_section(text: str) -> dict[str, object]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _divider() -> dict[str, object]:
    return {"type": "divider"}


# ---------------------------------------------------------------------------
# Public notification functions
# ---------------------------------------------------------------------------


def notify_human_gate(
    action: str,
    work_item_id: str,
    reason: str,
    pr_url: str | None = None,
) -> bool:
    """Notify the channel that a human decision gate was reached.

    Call this before the supervisor stops polling on ``human_merge`` or
    ``human_update_repo`` so the operator receives a link to act on.
    """
    action_label = action.replace("_", " ").upper()
    icon = ":white_check_mark:" if action == "human_merge" else ":traffic_light:"
    header = f"{icon} *{action_label}* — `{work_item_id}`"
    text = f"{header}\n{reason}"

    blocks: list[dict[str, object]] = [_mrkdwn_section(f"{header}\n_{reason}_")]
    if pr_url:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View PR"},
                        "style": "primary",
                        "url": pr_url,
                    }
                ],
            }
        )

    return _post_message(text, blocks)


def notify_runner_failed(
    work_item_id: str,
    runner_name: str,
    summary: str,
    *,
    retries_exhausted: bool,
) -> bool:
    """Notify when a runner has failed, optionally noting retries are exhausted."""
    if retries_exhausted:
        icon = ":sos:"
        label = "RETRIES EXHAUSTED — Runner Failed"
    else:
        icon = ":warning:"
        label = "Runner Failed (will retry)"

    text = f"{icon} *{label}*\n`{work_item_id}` | {runner_name}\n{summary}"
    return _post_message(text, [_mrkdwn_section(text)])


@dataclass(frozen=True)
class DigestLine:
    work_item_id: str
    runner_status: str | None
    outcome_status: str | None
    last_action: str | None
    updated_at: str | None


def send_morning_digest(db_path: Path, *, lookback_hours: int = 24) -> bool:
    """Query the last ``lookback_hours`` of activity and post a digest.

    Gracefully skips if no runs exist or no webhook is configured.
    """
    from agent_runtime.storage.sqlite import load_workflow_runs

    runs = load_workflow_runs(db_path)
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)

    merge_ready: list[str] = []
    blocked: list[str] = []
    failed: list[str] = []
    in_progress: list[str] = []

    for run in runs:
        if run.updated_at:
            try:
                ts = datetime.fromisoformat(run.updated_at.replace(" ", "T") + "+00:00")
                if ts < cutoff:
                    continue
            except ValueError:
                pass

        if run.last_action == "human_merge":
            merge_ready.append(run.work_item_id)
        elif run.runner_status == "completed":
            if run.outcome_status in {"blocked", "split_required"}:
                blocked.append(run.work_item_id)
            else:
                in_progress.append(run.work_item_id)
        elif run.runner_status in {"failed", "timed_out"}:
            failed.append(run.work_item_id)

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    lines: list[str] = [f":robot_face: *Agent Runtime Digest* — {date_str}"]

    if merge_ready:
        lines.append(f":white_check_mark: *Ready to merge:* {', '.join(f'`{w}`' for w in merge_ready)}")
    if blocked:
        lines.append(f":warning: *Blocked:* {', '.join(f'`{w}`' for w in blocked)}")
    if failed:
        lines.append(f":sos: *Failed:* {', '.join(f'`{w}`' for w in failed)}")
    if in_progress:
        lines.append(f":arrows_counterclockwise: *In progress:* {', '.join(f'`{w}`' for w in in_progress)}")
    if not (merge_ready or blocked or failed or in_progress):
        lines.append("_No agent activity in the last 24 hours._")

    text = "\n".join(lines)
    return _post_message(text, [_mrkdwn_section(text)])

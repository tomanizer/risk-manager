"""Tests for the Slack notification module (Iter 2)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


from alterraflow.notifications.slack import (
    notify_human_gate,
    notify_runner_failed,
    send_morning_digest,
)


class TestNotifyHumanGate:
    def test_returns_false_when_no_webhook_configured(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            original = os.environ.pop("SLACK_WEBHOOK_URL", None)
            try:
                result = notify_human_gate("human_merge", "WI-1", "reason")
                assert result is False
            finally:
                if original is not None:
                    os.environ["SLACK_WEBHOOK_URL"] = original

    def test_posts_when_webhook_configured(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            with patch("urllib.request.urlopen", return_value=mock_response):
                result = notify_human_gate("human_merge", "WI-1.1.4", "PR is ready to merge", pr_url="https://github.com/x/y/pull/42")
        assert result is True

    def test_returns_false_on_url_error(self) -> None:
        import urllib.error

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
                result = notify_human_gate("human_update_repo", "WI-2", "needs human update")
        assert result is False


class TestNotifyRunnerFailed:
    def test_returns_false_without_webhook(self) -> None:
        import os

        original = os.environ.pop("SLACK_WEBHOOK_URL", None)
        try:
            result = notify_runner_failed("WI-1", "coding", "timed out", retries_exhausted=True)
            assert result is False
        finally:
            if original is not None:
                os.environ["SLACK_WEBHOOK_URL"] = original

    def test_retries_exhausted_label(self) -> None:
        posted_payloads: list[bytes] = []

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        def capture_request(req: object, timeout: int = 10) -> MagicMock:
            posted_payloads.append(req.data)  # type: ignore[attr-defined]
            return mock_response

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            with patch("urllib.request.urlopen", side_effect=capture_request):
                notify_runner_failed("WI-1", "coding", "summary", retries_exhausted=True)

        assert posted_payloads
        payload = json.loads(posted_payloads[0])
        assert "RETRIES EXHAUSTED" in payload["text"]


class TestSendMorningDigest:
    def test_no_db_posts_no_activity_message(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        posted_payloads: list[bytes] = []

        def capture_request(req: object, timeout: int = 10) -> MagicMock:
            posted_payloads.append(req.data)  # type: ignore[attr-defined]
            return mock_response

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.db"
            with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
                with patch("urllib.request.urlopen", side_effect=capture_request):
                    result = send_morning_digest(db_path)

        assert result is True
        payload = json.loads(posted_payloads[0])
        assert "Digest" in payload["text"]
        assert "No agent activity" in payload["text"]

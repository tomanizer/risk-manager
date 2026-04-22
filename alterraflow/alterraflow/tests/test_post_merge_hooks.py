"""Tests for post-merge hooks (Iter 5)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch


from alterraflow.config.defaults import RuntimeDefaults
from alterraflow.orchestrator.post_merge_hooks import run_post_merge_hooks
from alterraflow.storage.sqlite import initialize_database, load_workflow_events


def _make_defaults(tmp_dir: str) -> RuntimeDefaults:
    return RuntimeDefaults(repo_root=Path(tmp_dir))


class TestRunPostMergeHooks:
    def test_writes_evidence_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            initialize_database(defaults.state_db_path)

            with patch("alterraflow.orchestrator.post_merge_hooks._run_drift_suite", return_value=(0, 10)):
                with patch("alterraflow.orchestrator.post_merge_hooks._git_head_sha", return_value="abc123"):
                    result = run_post_merge_hooks(defaults, work_item_id="WI-1.1.4", pr_url="https://github.com/x/y/pull/42", run_id="run-001")

            assert result["evidence_written"] is True
            assert result["drift_new_findings"] == 0
            assert result["drift_total_findings"] == 10

            events = load_workflow_events(defaults.state_db_path, "WI-1.1.4")
            actions = {e.action for e in events}
            assert "post_merge_evidence" in actions
            assert "drift_scan_post_merge" in actions

    def test_evidence_event_contains_commit_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            initialize_database(defaults.state_db_path)

            with patch("alterraflow.orchestrator.post_merge_hooks._run_drift_suite", return_value=(0, 5)):
                with patch("alterraflow.orchestrator.post_merge_hooks._git_head_sha", return_value="deadbeef"):
                    run_post_merge_hooks(defaults, work_item_id="WI-1.2.0", run_id="run-x")

            events = load_workflow_events(defaults.state_db_path, "WI-1.2.0")
            evidence_events = [e for e in events if e.action == "post_merge_evidence"]
            assert evidence_events
            assert evidence_events[0].details is not None
            assert evidence_events[0].details.get("commit_sha") == "deadbeef"

    def test_nonzero_drift_findings_logged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults = _make_defaults(tmp)
            initialize_database(defaults.state_db_path)

            with patch("alterraflow.orchestrator.post_merge_hooks._run_drift_suite", return_value=(3, 15)):
                with patch("alterraflow.orchestrator.post_merge_hooks._git_head_sha", return_value="sha1"):
                    result = run_post_merge_hooks(defaults, work_item_id="WI-2")

            assert result["drift_new_findings"] == 3

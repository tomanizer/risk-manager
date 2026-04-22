"""Tests for automatic PR publication after completed coding runs."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from alterraflow.config.defaults import RuntimeDefaults
from alterraflow.orchestrator.graph import run_runtime_step
from alterraflow.orchestrator.pr_publication import (
    PullRequestPublicationResult,
    maybe_publish_completed_coding_run,
)
from alterraflow.orchestrator.state import NextActionType, RuntimeSnapshot, TransitionDecision, WorkItemSnapshot, WorkItemStage
from alterraflow.runners.contracts import RunnerDispatchStatus, RunnerExecution, RunnerName, RunnerResult
from alterraflow.storage.sqlite import WorktreeLeaseRecord, load_workflow_run

from alterraflow.orchestrator.github_sync import GitHubRepository


def test_maybe_publish_completed_coding_run_creates_draft_pr() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        worktree_path = Path(temp_dir)
        execution = RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the coding agent.",
            metadata={
                "worktree_path": str(worktree_path),
                "branch_name": "codex/wi-1-1-4-test",
                "base_ref": "origin/main",
            },
        )
        runner_result = RunnerResult(
            runner_name=RunnerName.CODING,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.COMPLETED,
            summary="Completed coding run.",
            prompt=execution.prompt,
            details={},
            outcome_status="completed",
            outcome_summary="Implemented the requested slice and updated tests.",
            outcome_details={"changed_paths": "src/foo.py"},
        )

        responses = iter(
            [
                subprocess.CompletedProcess(["git"], 0, stdout="0 2\n", stderr=""),
                subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
                subprocess.CompletedProcess(["gh"], 0, stdout="[]", stderr=""),
                subprocess.CompletedProcess(["gh"], 0, stdout="https://github.com/tomanizer/risk-manager/pull/88\n", stderr=""),
                subprocess.CompletedProcess(
                    ["gh"],
                    0,
                    stdout=json.dumps(
                        [
                            {
                                "number": 88,
                                "url": "https://github.com/tomanizer/risk-manager/pull/88",
                            }
                        ]
                    ),
                    stderr="",
                ),
            ]
        )

        def fake_run(
            command: list[str],
            cwd: str | Path | None,
            check: bool,
            capture_output: bool,
            text: bool,
        ) -> subprocess.CompletedProcess[str]:
            del cwd, check, capture_output, text
            result = next(responses)
            assert isinstance(command, list)
            return result

        with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_PR_BACKEND": "gh_draft"}, clear=False):
            with patch(
                "alterraflow.orchestrator.pr_publication.infer_github_repository", return_value=GitHubRepository("tomanizer", "risk-manager")
            ):
                with patch("alterraflow.orchestrator.pr_publication.subprocess.run", side_effect=fake_run):
                    publication = maybe_publish_completed_coding_run(Path("/repo"), execution, runner_result)

    assert publication is not None
    assert publication.status == "published"
    assert publication.pr_number == 88
    assert publication.pr_url == "https://github.com/tomanizer/risk-manager/pull/88"


def test_maybe_publish_completed_coding_run_reuses_existing_pr() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        worktree_path = Path(temp_dir)
        execution = RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the coding agent.",
            metadata={
                "worktree_path": str(worktree_path),
                "branch_name": "codex/wi-1-1-4-test",
                "base_ref": "origin/main",
            },
        )
        runner_result = RunnerResult(
            runner_name=RunnerName.CODING,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.COMPLETED,
            summary="Completed coding run.",
            prompt=execution.prompt,
            outcome_status="completed",
            outcome_summary="Implemented the requested slice and updated tests.",
        )

        responses = iter(
            [
                subprocess.CompletedProcess(["git"], 0, stdout="0 1\n", stderr=""),
                subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
                subprocess.CompletedProcess(
                    ["gh"],
                    0,
                    stdout=json.dumps(
                        [
                            {
                                "number": 89,
                                "url": "https://github.com/tomanizer/risk-manager/pull/89",
                            }
                        ]
                    ),
                    stderr="",
                ),
            ]
        )

        def fake_run(
            command: list[str],
            cwd: str | Path | None,
            check: bool,
            capture_output: bool,
            text: bool,
        ) -> subprocess.CompletedProcess[str]:
            del cwd, check, capture_output, text
            return next(responses)

        with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_PR_BACKEND": "gh_draft"}, clear=False):
            with patch(
                "alterraflow.orchestrator.pr_publication.infer_github_repository", return_value=GitHubRepository("tomanizer", "risk-manager")
            ):
                with patch("alterraflow.orchestrator.pr_publication.subprocess.run", side_effect=fake_run):
                    publication = maybe_publish_completed_coding_run(Path("/repo"), execution, runner_result)

    assert publication is not None
    assert publication.status == "existing"
    assert publication.pr_number == 89


def test_maybe_publish_completed_coding_run_handles_missing_worktree() -> None:
    execution = RunnerExecution(
        runner_name=RunnerName.CODING,
        work_item_id="WI-1.1.4-risk-summary-core-service",
        prompt="Act only as the coding agent.",
        metadata={
            "worktree_path": "/tmp/definitely-missing-runtime-worktree",
            "branch_name": "codex/wi-1-1-4-test",
            "base_ref": "origin/main",
        },
    )
    runner_result = RunnerResult(
        runner_name=RunnerName.CODING,
        work_item_id=execution.work_item_id,
        status=RunnerDispatchStatus.COMPLETED,
        summary="Completed coding run.",
        prompt=execution.prompt,
        outcome_status="completed",
        outcome_summary="Implemented the requested slice and updated tests.",
    )

    with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_PR_BACKEND": "gh_draft"}, clear=False):
        publication = maybe_publish_completed_coding_run(Path("/repo"), execution, runner_result)

    assert publication is not None
    assert publication.status == "failed"
    assert "requires an existing worktree path" in publication.summary


def test_maybe_publish_completed_coding_run_handles_gh_list_oserror() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        worktree_path = Path(temp_dir)
        execution = RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the coding agent.",
            metadata={
                "worktree_path": str(worktree_path),
                "branch_name": "codex/wi-1-1-4-test",
                "base_ref": "origin/main",
            },
        )
        runner_result = RunnerResult(
            runner_name=RunnerName.CODING,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.COMPLETED,
            summary="Completed coding run.",
            prompt=execution.prompt,
            outcome_status="completed",
            outcome_summary="Implemented the requested slice and updated tests.",
        )

        responses = iter(
            [
                subprocess.CompletedProcess(["git"], 0, stdout="0 1\n", stderr=""),
                subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
            ]
        )

        def fake_run(
            command: list[str],
            cwd: str | Path | None,
            check: bool,
            capture_output: bool,
            text: bool,
        ) -> subprocess.CompletedProcess[str]:
            del cwd, check, capture_output, text
            if command[:2] == ["gh", "pr"]:
                raise OSError("gh not installed")
            return next(responses)

        with patch.dict("os.environ", {"AGENT_RUNTIME_CODING_PR_BACKEND": "gh_draft"}, clear=False):
            with patch(
                "alterraflow.orchestrator.pr_publication.infer_github_repository", return_value=GitHubRepository("tomanizer", "risk-manager")
            ):
                with patch("alterraflow.orchestrator.pr_publication.subprocess.run", side_effect=fake_run):
                    publication = maybe_publish_completed_coding_run(Path("/repo"), execution, runner_result)

        assert publication is not None
        assert publication.status == "failed"
        assert "could not inspect existing PRs" in publication.summary


def test_run_runtime_step_persists_published_pr_number() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_root = Path(temp_dir)
        (repo_root / "AGENTS.md").write_text("test\n", encoding="utf-8")
        (repo_root / "work_items" / "ready").mkdir(parents=True)
        work_item_path = repo_root / "work_items" / "ready" / "WI-1.1.4-risk-summary-core-service.md"
        work_item_path.write_text("# WI-1.1.4\n", encoding="utf-8")
        defaults = RuntimeDefaults(repo_root=repo_root)
        snapshot = RuntimeSnapshot(
            work_items=(
                WorkItemSnapshot(
                    id="WI-1.1.4-risk-summary-core-service",
                    title="WI-1.1.4",
                    path=work_item_path,
                    stage=WorkItemStage.READY,
                    dependencies=(),
                ),
            )
        )
        execution = RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id="WI-1.1.4-risk-summary-core-service",
            prompt="Act only as the coding agent.",
            metadata={"target_path": str(work_item_path)},
        )
        bound_execution = RunnerExecution(
            runner_name=RunnerName.CODING,
            work_item_id=execution.work_item_id,
            prompt=execution.prompt,
            metadata={
                "target_path": str(work_item_path),
                "run_id": "coding-wi-1-1-4-test-run",
                "branch_name": "codex/wi-1-1-4-test",
                "base_ref": "origin/main",
                "worktree_path": "/tmp/runtime-coding-worktree",
            },
        )
        runner_result = RunnerResult(
            runner_name=RunnerName.CODING,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.COMPLETED,
            summary="Completed coding run for WI-1.1.4-risk-summary-core-service.",
            prompt=execution.prompt,
            details={},
            outcome_status="completed",
            outcome_summary="Implemented the requested slice and updated tests.",
            outcome_details={"changed_paths": "src/foo.py"},
        )

        with patch(
            "alterraflow.orchestrator.graph.decide_next_action",
            return_value=TransitionDecision(
                action=NextActionType.RUN_CODING,
                work_item_id=execution.work_item_id,
                reason="ready for implementation",
                target_path=work_item_path,
            ),
        ):
            with patch("alterraflow.orchestrator.graph.build_runner_execution", return_value=execution):
                with patch(
                    "alterraflow.orchestrator.graph.allocate_worktree",
                    return_value=WorktreeLeaseRecord(
                        run_id="coding-wi-1-1-4-test-run",
                        work_item_id=execution.work_item_id,
                        runner_name="coding",
                        branch_name="codex/wi-1-1-4-test",
                        base_ref="origin/main",
                        worktree_path="/tmp/runtime-coding-worktree",
                        status="active",
                    ),
                ):
                    with patch("alterraflow.orchestrator.graph.bind_worktree_to_execution", return_value=bound_execution):
                        with patch("alterraflow.orchestrator.graph.dispatch_runner_execution", return_value=runner_result):
                            with patch(
                                "alterraflow.orchestrator.graph.maybe_publish_completed_coding_run",
                                return_value=PullRequestPublicationResult(
                                    status="published",
                                    summary="Published draft PR #91.",
                                    pr_number=91,
                                    pr_url="https://github.com/tomanizer/risk-manager/pull/91",
                                    details={"pr_publication_backend": "gh_draft"},
                                ),
                            ):
                                payload = run_runtime_step(
                                    defaults,
                                    snapshot,
                                    should_build_execution=True,
                                    should_dispatch=True,
                                )

        loaded = load_workflow_run(defaults.state_db_path, execution.work_item_id)

        assert loaded is not None
        assert loaded.pr_number == 91
        assert loaded.branch_name == "codex/wi-1-1-4-test"
        assert loaded.result["outcome_details"] == {
            "changed_paths": "src/foo.py",
            "pr_number": "91",
            "pr_publication_backend": "gh_draft",
            "pr_url": "https://github.com/tomanizer/risk-manager/pull/91",
        }
        assert payload["pr_publication"] == {
            "status": "published",
            "summary": "Published draft PR #91.",
            "pr_number": 91,
            "pr_url": "https://github.com/tomanizer/risk-manager/pull/91",
            "details": {"pr_publication_backend": "gh_draft"},
        }

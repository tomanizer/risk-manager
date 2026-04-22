"""Draft PR publication helpers for completed coding runs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess

from alterraflow.config.settings import get_settings
from alterraflow.runners.contracts import (
    RunnerDispatchStatus,
    RunnerExecution,
    RunnerName,
    RunnerResult,
)

from .github_sync import infer_github_repository

CODING_PR_BACKEND_DISABLED = "disabled"
CODING_PR_BACKEND_GH_DRAFT = "gh_draft"


@dataclass(frozen=True)
class PullRequestPublicationResult:
    status: str
    summary: str
    pr_number: int | None = None
    pr_url: str | None = None
    details: dict[str, str] = field(default_factory=dict)


def get_coding_pr_backend_name() -> str:
    cfg = get_settings().alterraflow
    return (cfg.coding_pr_backend or CODING_PR_BACKEND_DISABLED).strip().lower() or CODING_PR_BACKEND_DISABLED


def maybe_publish_completed_coding_run(
    repo_root: Path,
    execution: RunnerExecution | None,
    runner_result: RunnerResult | None,
) -> PullRequestPublicationResult | None:
    if execution is None or runner_result is None:
        return None
    if execution.runner_name is not RunnerName.CODING or runner_result.runner_name is not RunnerName.CODING:
        return None
    if runner_result.status is not RunnerDispatchStatus.COMPLETED or runner_result.outcome_status != "completed":
        return None
    if execution.metadata.get("pr_number"):
        return None

    backend_name = get_coding_pr_backend_name()
    if backend_name == CODING_PR_BACKEND_DISABLED:
        return None
    if backend_name != CODING_PR_BACKEND_GH_DRAFT:
        return PullRequestPublicationResult(
            status="failed",
            summary=f"Unsupported coding PR publication backend configured: {backend_name}",
            details={"pr_publication_backend": backend_name},
        )

    worktree_path = execution.metadata.get("worktree_path")
    branch_name = execution.metadata.get("branch_name")
    base_ref = execution.metadata.get("base_ref", "origin/main")
    if not worktree_path or not branch_name:
        return PullRequestPublicationResult(
            status="failed",
            summary="Coding PR publication requires an allocated worktree path and branch name.",
            details={"pr_publication_backend": backend_name},
        )
    if not Path(worktree_path).exists():
        return PullRequestPublicationResult(
            status="failed",
            summary=f"Coding PR publication requires an existing worktree path: {worktree_path}",
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )

    repository = infer_github_repository(repo_root)
    if repository is None:
        return PullRequestPublicationResult(
            status="failed",
            summary="Coding PR publication could not infer the GitHub repository from remote.origin.url.",
            details={"pr_publication_backend": backend_name},
        )

    try:
        ahead_count = _count_branch_ahead(Path(worktree_path), base_ref)
    except RuntimeError as error:
        return PullRequestPublicationResult(
            status="failed",
            summary=str(error),
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )
    if ahead_count is None:
        return PullRequestPublicationResult(
            status="failed",
            summary=f"Coding PR publication could not compare HEAD against {base_ref}.",
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )
    if ahead_count == 0:
        return PullRequestPublicationResult(
            status="failed",
            summary=f"Coding PR publication found no branch commits ahead of {base_ref}.",
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )

    push_error = _push_branch(Path(worktree_path), branch_name)
    if push_error is not None:
        return PullRequestPublicationResult(
            status="failed",
            summary=f"Coding PR publication failed to push branch {branch_name}: {push_error}",
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )

    try:
        existing_pr = _find_open_pull_request(repo_root, repository.full_name, branch_name)
    except RuntimeError as error:
        return PullRequestPublicationResult(
            status="failed",
            summary=str(error),
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )
    if existing_pr is not None:
        return PullRequestPublicationResult(
            status="existing",
            summary=f"Reused existing draft-ready PR #{existing_pr.pr_number} for {execution.work_item_id}.",
            pr_number=existing_pr.pr_number,
            pr_url=existing_pr.pr_url,
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )

    try:
        create_error = _create_draft_pull_request(
            repo_root=repo_root,
            repository_full_name=repository.full_name,
            work_item_id=execution.work_item_id,
            branch_name=branch_name,
            base_branch=_normalize_base_branch(base_ref),
        )
    except RuntimeError as error:
        return PullRequestPublicationResult(
            status="failed",
            summary=str(error),
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )
    if create_error is not None:
        return PullRequestPublicationResult(
            status="failed",
            summary=f"Coding PR publication failed to create a draft PR: {create_error}",
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )

    try:
        created_pr = _find_open_pull_request(repo_root, repository.full_name, branch_name)
    except RuntimeError as error:
        return PullRequestPublicationResult(
            status="failed",
            summary=str(error),
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )
    if created_pr is None:
        return PullRequestPublicationResult(
            status="failed",
            summary="Coding PR publication created a draft PR but could not resolve its number.",
            details={
                "pr_publication_backend": backend_name,
                "branch_name": branch_name,
                "base_ref": base_ref,
            },
        )

    return PullRequestPublicationResult(
        status="published",
        summary=f"Published draft PR #{created_pr.pr_number} for {execution.work_item_id}.",
        pr_number=created_pr.pr_number,
        pr_url=created_pr.pr_url,
        details={
            "pr_publication_backend": backend_name,
            "branch_name": branch_name,
            "base_ref": base_ref,
        },
    )


@dataclass(frozen=True)
class _ExistingPullRequest:
    pr_number: int
    pr_url: str | None


def _count_branch_ahead(worktree_path: Path, base_ref: str) -> int | None:
    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{base_ref}...HEAD"],
            cwd=worktree_path,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Coding PR publication failed to inspect branch ancestry: {error}") from error
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    if len(parts) != 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _push_branch(worktree_path: Path, branch_name: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=worktree_path,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        return f"git push could not start: {error}"
    if result.returncode == 0:
        return None
    return (result.stderr or result.stdout).strip() or f"git push exited with status {result.returncode}"


def _find_open_pull_request(
    repo_root: Path,
    repository_full_name: str,
    branch_name: str,
) -> _ExistingPullRequest | None:
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repository_full_name,
                "--head",
                branch_name,
                "--state",
                "open",
                "--json",
                "number,url",
            ],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Coding PR publication could not inspect existing PRs: {error}") from error
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if not isinstance(first, dict):
        return None
    raw_number = first.get("number")
    if isinstance(raw_number, bool) or not isinstance(raw_number, int):
        return None
    raw_url = first.get("url")
    pr_url = raw_url if isinstance(raw_url, str) else None
    return _ExistingPullRequest(pr_number=raw_number, pr_url=pr_url)


def _create_draft_pull_request(
    *,
    repo_root: Path,
    repository_full_name: str,
    work_item_id: str,
    branch_name: str,
    base_branch: str,
) -> str | None:
    title_prefix = get_settings().alterraflow.coding_pr_title_prefix.strip() or "[codex]"
    title = f"{title_prefix} Implement {work_item_id}"
    body = (
        "## Summary\n"
        f"- publish the completed coding run for `{work_item_id}`\n"
        "- keep the PR narrow and draft-gated for governed review\n\n"
        "## Runtime\n"
        "- opened automatically by `alterraflow`\n"
        f"- branch: `{branch_name}`\n"
    )
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repository_full_name,
                "--draft",
                "--base",
                base_branch,
                "--head",
                branch_name,
                "--title",
                title,
                "--body",
                body,
            ],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Coding PR publication could not create a draft PR: {error}") from error
    if result.returncode == 0:
        return None
    return (result.stderr or result.stdout).strip() or f"gh pr create exited with status {result.returncode}"


def _normalize_base_branch(base_ref: str) -> str:
    if base_ref.startswith("origin/"):
        return base_ref.removeprefix("origin/")
    return base_ref

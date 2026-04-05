"""Live GitHub PR sync for the runtime orchestrator."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, cast

from .state import PullRequestSnapshot, WorkItemSnapshot

_REMOTE_GITHUB_PATTERNS = (
    re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$"),
    re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$"),
)

_OPEN_PULL_REQUESTS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      first: 50
      states: OPEN
      orderBy: {field: UPDATED_AT, direction: DESC}
      after: $cursor
    ) {
      nodes {
        number
        url
        isDraft
        headRefName
        title
        body
        reviewDecision
        mergeStateStatus
        reviewThreads(first: 100) {
          nodes {
            isResolved
          }
        }
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state
              }
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


def parse_github_remote(remote_url: str) -> GitHubRepository | None:
    for pattern in _REMOTE_GITHUB_PATTERNS:
        match = pattern.match(remote_url.strip())
        if match is not None:
            return GitHubRepository(owner=match.group("owner"), name=match.group("name"))
    return None


def infer_github_repository(repo_root: Path) -> GitHubRepository | None:
    command = ["git", "config", "--get", "remote.origin.url"]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return parse_github_remote(result.stdout)


def _run_gh_graphql(repo_root: Path, *, query: str, variables: dict[str, str | None]) -> dict[str, object]:
    command = [
        "gh",
        "api",
        "graphql",
        "--field",
        f"query={query}",
    ]
    for name, value in variables.items():
        if value is None:
            continue
        command.extend(["--field", f"{name}={value}"])
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh api failure"
        raise RuntimeError(stderr)
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("gh graphql payload was not a JSON object")
    return cast(dict[str, object], payload)


def _extract_work_item_reference(
    node: dict[str, object],
    known_work_item_ids: tuple[str, ...],
) -> tuple[str | None, str | None]:
    head_ref_name = str(node.get("headRefName") or "")
    title = str(node.get("title") or "")
    body = str(node.get("body") or "")

    head_ref_matches = _find_work_item_matches(head_ref_name, known_work_item_ids)
    if len(head_ref_matches) == 1:
        return head_ref_matches[0], None
    if len(head_ref_matches) > 1:
        return None, f"PR #{node.get('number')} matched multiple work items in branch: {', '.join(head_ref_matches)}"

    title_matches = _find_work_item_matches(title, known_work_item_ids)
    if len(title_matches) == 1:
        return title_matches[0], None
    if len(title_matches) > 1:
        return None, f"PR #{node.get('number')} matched multiple work items in title: {', '.join(title_matches)}"

    body_matches = _find_work_item_matches(body, known_work_item_ids)
    if len(body_matches) == 1:
        return body_matches[0], None
    if len(body_matches) > 1:
        return None, f"PR #{node.get('number')} matched multiple work items in body: {', '.join(body_matches)}"

    return None, None


def _find_work_item_matches(text: str, known_work_item_ids: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for candidate_id in sorted(known_work_item_ids, key=len, reverse=True):
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(candidate_id)}(?![A-Za-z0-9])")
        if pattern.search(text):
            matches.append(candidate_id)
    return matches


def _extract_ci_status(node: dict[str, object]) -> str | None:
    commits = node.get("commits")
    if not isinstance(commits, dict):
        return None
    commit_nodes = commits.get("nodes")
    if not isinstance(commit_nodes, list) or not commit_nodes:
        return None
    commit = commit_nodes[-1]
    if not isinstance(commit, dict):
        return None
    inner_commit = commit.get("commit")
    if not isinstance(inner_commit, dict):
        return None
    status_rollup = inner_commit.get("statusCheckRollup")
    if not isinstance(status_rollup, dict):
        return None
    state = status_rollup.get("state")
    return str(state) if state else None


def build_pull_request_snapshots(
    payload: Mapping[str, object],
    work_items: tuple[WorkItemSnapshot, ...],
) -> tuple[tuple[PullRequestSnapshot, ...], tuple[str, ...]]:
    nodes, payload_warnings = _extract_pull_request_nodes(payload)

    if nodes is None:
        return (), payload_warnings

    known_work_item_ids = tuple(item.id for item in work_items)
    snapshots_by_work_item: dict[str, PullRequestSnapshot] = {}
    warnings: list[str] = list(payload_warnings)

    for raw_node in nodes:
        if not isinstance(raw_node, dict):
            warnings.append("GitHub sync skipped a non-dictionary pull request node")
            continue
        work_item_id, warning = _extract_work_item_reference(raw_node, known_work_item_ids)
        if warning is not None:
            warnings.append(warning)
            continue
        if work_item_id is None:
            continue
        raw_number = raw_node.get("number")
        if isinstance(raw_number, bool) or not isinstance(raw_number, int | str):
            number = None
        else:
            try:
                number = int(raw_number)
            except ValueError:
                number = None
        if number is None:
            warnings.append(f"GitHub sync skipped malformed PR node for work item {work_item_id}: missing or invalid number")
            continue

        review_threads = raw_node.get("reviewThreads")
        thread_nodes: list[object] = []
        if isinstance(review_threads, dict):
            raw_thread_nodes = review_threads.get("nodes")
            if isinstance(raw_thread_nodes, list):
                thread_nodes = raw_thread_nodes
        unresolved_review_threads = len([thread for thread in thread_nodes if isinstance(thread, dict) and thread.get("isResolved") is False])
        review_decision = str(raw_node.get("reviewDecision")) if raw_node.get("reviewDecision") else None

        if work_item_id in snapshots_by_work_item:
            warnings.append(
                f"GitHub sync found multiple open PRs for {work_item_id}; keeping newer PR #{snapshots_by_work_item[work_item_id].number} and skipping PR #{number}"
            )
            continue

        snapshots_by_work_item[work_item_id] = PullRequestSnapshot(
            work_item_id=work_item_id,
            number=number,
            is_draft=bool(raw_node.get("isDraft")),
            url=str(raw_node.get("url")) if raw_node.get("url") else None,
            head_ref_name=str(raw_node.get("headRefName")) if raw_node.get("headRefName") else None,
            unresolved_review_threads=unresolved_review_threads,
            has_new_review_comments=False,
            review_decision=review_decision,
            merge_state_status=str(raw_node.get("mergeStateStatus")) if raw_node.get("mergeStateStatus") else None,
            ci_status=_extract_ci_status(raw_node),
        )
    return tuple(snapshots_by_work_item.values()), tuple(warnings)


def fetch_pull_requests(
    repo_root: Path,
    work_items: tuple[WorkItemSnapshot, ...],
) -> tuple[tuple[PullRequestSnapshot, ...], tuple[str, ...]]:
    if not work_items:
        return (), ()

    repository = infer_github_repository(repo_root)
    if repository is None:
        return (), ("could not infer GitHub repository from remote.origin.url",)

    raw_nodes: list[dict[str, object]] = []
    warnings: list[str] = []
    cursor: str | None = None

    try:
        while True:
            payload = _run_gh_graphql(
                repo_root,
                query=_OPEN_PULL_REQUESTS_QUERY,
                variables={"owner": repository.owner, "name": repository.name, "cursor": cursor},
            )
            page_nodes, page_warnings, page_info = _extract_pull_request_page(payload)
            warnings.extend(page_warnings)
            if page_nodes is None:
                break
            raw_nodes.extend(page_nodes)
            if not page_info["has_next_page"]:
                break
            raw_end_cursor = page_info["end_cursor"]
            cursor = raw_end_cursor if isinstance(raw_end_cursor, str) else None
            if cursor is None:
                warnings.append("GitHub sync saw hasNextPage without endCursor; stopping pagination early")
                break
    except FileNotFoundError:
        return (), ("gh CLI is not installed; skipping live GitHub PR sync",)
    except RuntimeError as exc:
        return (), (f"GitHub PR sync failed: {exc}",)

    snapshots, snapshot_warnings = build_pull_request_snapshots(
        {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": raw_nodes,
                    }
                }
            }
        },
        work_items,
    )
    return snapshots, tuple(warnings) + snapshot_warnings


def _extract_pull_request_nodes(payload: Mapping[str, object]) -> tuple[list[dict[str, object]] | None, tuple[str, ...]]:
    data = payload.get("data")
    repository = data.get("repository") if isinstance(data, dict) else None
    pull_requests = repository.get("pullRequests") if isinstance(repository, dict) else None
    nodes = pull_requests.get("nodes") if isinstance(pull_requests, dict) else None
    if not isinstance(nodes, list):
        return None, ("GitHub sync payload did not include pull request nodes",)
    return [node for node in nodes if isinstance(node, dict)], ()


def _extract_pull_request_page(
    payload: Mapping[str, object],
) -> tuple[list[dict[str, object]] | None, tuple[str, ...], dict[str, str | bool | None]]:
    data = payload.get("data")
    repository = data.get("repository") if isinstance(data, dict) else None
    pull_requests = repository.get("pullRequests") if isinstance(repository, dict) else None
    nodes = pull_requests.get("nodes") if isinstance(pull_requests, dict) else None
    page_info = pull_requests.get("pageInfo") if isinstance(pull_requests, dict) else None

    if not isinstance(nodes, list):
        return None, ("GitHub sync payload did not include pull request nodes",), {"has_next_page": False, "end_cursor": None}
    if not isinstance(page_info, dict):
        return (
            [node for node in nodes if isinstance(node, dict)],
            ("GitHub sync payload did not include pageInfo; stopping after first page",),
            {
                "has_next_page": False,
                "end_cursor": None,
            },
        )

    return (
        [node for node in nodes if isinstance(node, dict)],
        (),
        {
            "has_next_page": bool(page_info.get("hasNextPage")),
            "end_cursor": str(page_info.get("endCursor")) if page_info.get("endCursor") else None,
        },
    )

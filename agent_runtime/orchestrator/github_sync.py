"""Live GitHub PR sync for the runtime orchestrator."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .state import PullRequestSnapshot, WorkItemSnapshot

_REMOTE_GITHUB_PATTERNS = (
    re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<name>[^/.]+?)(?:\.git)?$"),
    re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<name>[^/.]+?)(?:\.git)?$"),
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
    return json.loads(result.stdout)


def _extract_work_item_reference(
    node: dict[str, object],
    known_work_item_ids: tuple[str, ...],
) -> tuple[str | None, str | None]:
    head_ref_name = str(node.get("headRefName") or "")
    title = str(node.get("title") or "")
    body = str(node.get("body") or "")

    for candidate_id in known_work_item_ids:
        if candidate_id in head_ref_name:
            return candidate_id, None

    title_matches = [candidate_id for candidate_id in known_work_item_ids if candidate_id in title]
    if len(title_matches) == 1:
        return title_matches[0], None
    if len(title_matches) > 1:
        return None, f"PR #{node.get('number')} matched multiple work items in title: {', '.join(title_matches)}"

    body_matches = [candidate_id for candidate_id in known_work_item_ids if candidate_id in body]
    if len(body_matches) == 1:
        return body_matches[0], None
    if len(body_matches) > 1:
        return None, f"PR #{node.get('number')} matched multiple work items in body: {', '.join(body_matches)}"

    return None, None


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
    payload: dict[str, object],
    work_items: tuple[WorkItemSnapshot, ...],
) -> tuple[tuple[PullRequestSnapshot, ...], tuple[str, ...]]:
    repository = payload.get("data", {}).get("repository") if isinstance(payload.get("data"), dict) else None
    pull_requests = repository.get("pullRequests") if isinstance(repository, dict) else None
    nodes = pull_requests.get("nodes") if isinstance(pull_requests, dict) else None

    if not isinstance(nodes, list):
        return (), ("GitHub sync payload did not include pull request nodes",)

    known_work_item_ids = tuple(item.id for item in work_items)
    snapshots: list[PullRequestSnapshot] = []
    warnings: list[str] = []

    for raw_node in nodes:
        if not isinstance(raw_node, dict):
            continue
        work_item_id, warning = _extract_work_item_reference(raw_node, known_work_item_ids)
        if warning is not None:
            warnings.append(warning)
            continue
        if work_item_id is None:
            continue

        review_threads = raw_node.get("reviewThreads")
        thread_nodes = review_threads.get("nodes") if isinstance(review_threads, dict) else []
        unresolved_review_threads = sum(1 for thread in thread_nodes if isinstance(thread, dict) and thread.get("isResolved") is False)
        review_decision = str(raw_node.get("reviewDecision")) if raw_node.get("reviewDecision") else None

        snapshots.append(
            PullRequestSnapshot(
                work_item_id=work_item_id,
                number=int(raw_node["number"]),
                is_draft=bool(raw_node.get("isDraft")),
                url=str(raw_node.get("url")) if raw_node.get("url") else None,
                head_ref_name=str(raw_node.get("headRefName")) if raw_node.get("headRefName") else None,
                unresolved_review_threads=unresolved_review_threads,
                has_new_review_comments=review_decision == "CHANGES_REQUESTED",
                review_decision=review_decision,
                merge_state_status=str(raw_node.get("mergeStateStatus")) if raw_node.get("mergeStateStatus") else None,
                ci_status=_extract_ci_status(raw_node),
            )
        )

    return tuple(snapshots), tuple(warnings)


def fetch_pull_requests(
    repo_root: Path,
    work_items: tuple[WorkItemSnapshot, ...],
) -> tuple[tuple[PullRequestSnapshot, ...], tuple[str, ...]]:
    if not work_items:
        return (), ()

    repository = infer_github_repository(repo_root)
    if repository is None:
        return (), ("could not infer GitHub repository from remote.origin.url",)

    try:
        payload = _run_gh_graphql(
            repo_root,
            query=_OPEN_PULL_REQUESTS_QUERY,
            variables={"owner": repository.owner, "name": repository.name},
        )
    except FileNotFoundError:
        return (), ("gh CLI is not installed; skipping live GitHub PR sync",)
    except RuntimeError as exc:
        return (), (f"GitHub PR sync failed: {exc}",)

    return build_pull_request_snapshots(payload, work_items)

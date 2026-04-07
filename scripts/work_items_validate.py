#!/usr/bin/env python3
"""Validate work-item folder consistency from git-tracked state.

Usage:
  python scripts/work_items_validate.py
  python scripts/work_items_validate.py --ref origin/main
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WI_PATTERN = re.compile(r"(WI-\d+\.\d+\.\d+)")


@dataclass(frozen=True)
class WorkItem:
    wi_id: str
    path: str
    dependencies: tuple[str, ...]


def _run_git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _tracked_paths(repo_root: Path, ref: str, folder: str) -> list[str]:
    out = _run_git(["ls-tree", "-r", "--name-only", ref, folder], repo_root)
    return [line.strip() for line in out.splitlines() if line.strip().endswith(".md")]


def _read_tracked_file(repo_root: Path, ref: str, path: str) -> str:
    return _run_git(["show", f"{ref}:{path}"], repo_root)


def _parse_work_item(path: str, text: str) -> WorkItem:
    header_match = re.search(r"^#\s+(WI-\S+)", text, re.MULTILINE)
    if header_match:
        wi_id = header_match.group(1)
    else:
        file_match = WI_PATTERN.search(Path(path).name)
        wi_id = file_match.group(1) if file_match else Path(path).stem

    deps: list[str] = []
    dep_section = re.search(r"^##\s+Dependencies\s*$([\s\S]*?)(?:^##\s+|\Z)", text, re.MULTILINE)
    if dep_section:
        for dep in WI_PATTERN.findall(dep_section.group(1)):
            deps.append(dep)

    return WorkItem(wi_id=wi_id, path=path, dependencies=tuple(dict.fromkeys(deps)))


def _collect(repo_root: Path, ref: str, folder: str) -> dict[str, WorkItem]:
    items: dict[str, WorkItem] = {}
    for path in _tracked_paths(repo_root, ref, folder):
        wi = _parse_work_item(path, _read_tracked_file(repo_root, ref, path))
        items[wi.wi_id] = wi
    return items


def validate(repo_root: Path, ref: str) -> list[str]:
    errors: list[str] = []
    ready = _collect(repo_root, ref, "work_items/ready")
    done = _collect(repo_root, ref, "work_items/done")

    overlap = sorted(set(ready) & set(done))
    if overlap:
        errors.append(f"Duplicate WI IDs in both ready and done: {', '.join(overlap)}")

    all_known = set(ready) | set(done)
    for wi in sorted(ready.values(), key=lambda x: x.wi_id):
        missing = [dep for dep in wi.dependencies if dep not in done and dep in all_known]
        unresolved = [dep for dep in wi.dependencies if dep not in all_known]
        if missing:
            errors.append(f"{wi.wi_id} depends on not-done items: {', '.join(missing)}")
        if unresolved:
            errors.append(f"{wi.wi_id} lists unknown dependencies: {', '.join(unresolved)}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate WI folder consistency.")
    parser.add_argument("--ref", default="HEAD", help="Git ref to validate (default: HEAD).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    try:
        issues = validate(repo_root, args.ref)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not issues:
        print(f"OK: work item state is consistent at {args.ref}.")
        return 0

    print(f"FAILED: work item state has {len(issues)} issue(s) at {args.ref}:")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

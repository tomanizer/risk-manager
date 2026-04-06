#!/usr/bin/env python3
"""Aggregate agent outcome scores into a quality report.

Usage:
    python scripts/outcome_report.py
    python scripts/outcome_report.py --role coding
    python scripts/outcome_report.py --work-item WI-1.1.4
    python scripts/outcome_report.py --format markdown

Output shows trends per role and per work item:
    - relay completion rate (runs without human_override)
    - median review rounds
    - stop condition violation rate
    - scope respect rate
    - test green rate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def find_repo_root(start: Path) -> Path:
    candidate = start if start.is_dir() else start.parent
    for path in (candidate, *candidate.parents):
        if (path / "AGENTS.md").exists() and (path / "work_items").is_dir():
            return path
    raise RuntimeError("Could not find repository root.")


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator // denominator}%"


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return float(sorted_vals[mid])


def _summarise(scores: list[Any]) -> dict[str, object]:
    total = len(scores)
    if total == 0:
        return {"total_runs": 0}
    stop_ok = sum(1 for s in scores if s.passed_stop_conditions)
    scope_ok = sum(1 for s in scores if s.scope_respected)
    tests_ok = sum(1 for s in scores if s.tests_green)
    no_override = sum(1 for s in scores if not s.human_override)
    review_rounds = [s.review_rounds for s in scores]
    return {
        "total_runs": total,
        "relay_completion_rate": _pct(no_override, total),
        "stop_condition_pass_rate": _pct(stop_ok, total),
        "scope_respect_rate": _pct(scope_ok, total),
        "test_green_rate": _pct(tests_ok, total),
        "median_review_rounds": _median(review_rounds),
        "human_override_count": total - no_override,
    }


def _by_role(scores: list[Any]) -> dict[str, dict[str, object]]:
    by: dict[str, list[Any]] = {}
    for s in scores:
        by.setdefault(s.role, []).append(s)
    return {role: _summarise(role_scores) for role, role_scores in sorted(by.items())}


def _by_work_item(scores: list[Any]) -> dict[str, dict[str, object]]:
    by: dict[str, list[Any]] = {}
    for s in scores:
        by.setdefault(s.work_item_id, []).append(s)
    return {wi: _summarise(wi_scores) for wi, wi_scores in sorted(by.items())}


def _render_markdown(report: dict[str, object]) -> str:
    lines: list[str] = ["# Agent Outcome Report\n"]

    overall = report.get("overall", {})
    lines.append("## Overall\n")
    lines.append(f"- Total scored runs: {overall.get('total_runs', 0)}")
    lines.append(f"- Relay completion rate: {overall.get('relay_completion_rate', 'n/a')}")
    lines.append(f"- Stop condition pass rate: {overall.get('stop_condition_pass_rate', 'n/a')}")
    lines.append(f"- Scope respect rate: {overall.get('scope_respect_rate', 'n/a')}")
    lines.append(f"- Test green rate: {overall.get('test_green_rate', 'n/a')}")
    lines.append(f"- Median review rounds: {overall.get('median_review_rounds', 'n/a')}")
    lines.append(f"- Human override count: {overall.get('human_override_count', 0)}")
    lines.append("")

    by_role = report.get("by_role", {})
    if by_role:
        lines.append("## By Role\n")
        lines.append("| Role | Runs | Completion | Stop OK | Scope OK | Tests OK | Median Reviews |")
        lines.append("|------|------|-----------|---------|----------|----------|----------------|")
        for role, stats in by_role.items():
            lines.append(
                f"| {role} | {stats.get('total_runs')} | {stats.get('relay_completion_rate')} "
                f"| {stats.get('stop_condition_pass_rate')} | {stats.get('scope_respect_rate')} "
                f"| {stats.get('test_green_rate')} | {stats.get('median_review_rounds')} |"
            )
        lines.append("")

    by_wi = report.get("by_work_item", {})
    if by_wi:
        lines.append("## By Work Item\n")
        lines.append("| Work Item | Runs | Completion | Override Count |")
        lines.append("|-----------|------|-----------|----------------|")
        for wi, stats in by_wi.items():
            lines.append(f"| {wi} | {stats.get('total_runs')} | {stats.get('relay_completion_rate')} | {stats.get('human_override_count')} |")
        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate agent outcome scores into a quality report.")
    parser.add_argument("--role", default=None, help="Filter by agent role.")
    parser.add_argument("--work-item", default=None, help="Filter by work item ID.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument("--db", default=None, help="Path to the state database. Defaults to auto-detected.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = find_repo_root(Path.cwd())
    sys.path.insert(0, str(repo_root))

    from agent_runtime.config.defaults import build_defaults
    from agent_runtime.storage.sqlite import load_agent_outcome_scores

    defaults = build_defaults(repo_root)
    db_path = Path(args.db) if args.db else defaults.state_db_path

    if not db_path.exists():
        print(json.dumps({"total_runs": 0, "message": "No scores recorded yet."}, indent=2))
        return 0

    scores = load_agent_outcome_scores(
        db_path,
        work_item_id=args.work_item,
        role=args.role,
    )

    report: dict[str, object] = {
        "overall": _summarise(scores),
        "by_role": _by_role(scores),
        "by_work_item": _by_work_item(scores),
        "db_path": str(db_path),
        "filters": {
            "role": args.role,
            "work_item": args.work_item,
        },
    }

    if args.format == "markdown":
        print(_render_markdown(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

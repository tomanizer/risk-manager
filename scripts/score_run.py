#!/usr/bin/env python3
"""Record a human quality score for a completed agent run.

Usage:
    python scripts/score_run.py \\
        --run-id <RUN_ID> \\
        --work-item WI-1.1.4 \\
        --role coding \\
        [--failed-stop-conditions] \\
        [--scope-violated] \\
        [--tests-red] \\
        [--review-rounds 2] \\
        [--human-override] \\
        [--notes "Had to manually fix the shared error path"]

The score is stored in the agent runtime SQLite database alongside the
workflow run record and can be aggregated with `scripts/outcome_report.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    candidate = start if start.is_dir() else start.parent
    for path in (candidate, *candidate.parents):
        if (path / "AGENTS.md").exists() and (path / "work_items").is_dir():
            return path
    raise RuntimeError("Could not find repository root.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a human quality score for a completed agent run.",
    )
    parser.add_argument("--run-id", required=True, help="Run ID from the workflow run record.")
    parser.add_argument("--work-item", required=True, help="Work item ID, e.g. WI-1.1.4-risk-summary-core-service.")
    parser.add_argument(
        "--role",
        required=True,
        choices=["pm", "spec", "issue_planner", "coding", "review", "drift_monitor"],
        help="Agent role that produced this run.",
    )
    parser.add_argument(
        "--failed-stop-conditions",
        action="store_true",
        help="Mark this run as having violated one or more stop conditions.",
    )
    parser.add_argument(
        "--scope-violated",
        action="store_true",
        help="Mark this run as having violated scope boundaries.",
    )
    parser.add_argument(
        "--tests-red",
        action="store_true",
        help="Mark this run as having left tests failing.",
    )
    parser.add_argument(
        "--review-rounds",
        type=int,
        default=0,
        help="Number of review rounds required before merge (default: 0).",
    )
    parser.add_argument(
        "--human-override",
        action="store_true",
        help="Mark that a human had to override or substantially rewrite the agent output.",
    )
    parser.add_argument("--notes", default=None, help="Free-form notes about this run.")
    parser.add_argument("--db", default=None, help="Path to the state database. Defaults to auto-detected.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = find_repo_root(Path.cwd())
    sys.path.insert(0, str(repo_root))

    from agent_runtime.config.defaults import build_defaults
    from agent_runtime.storage.sqlite import AgentOutcomeScore, record_agent_outcome_score

    defaults = build_defaults(repo_root)
    db_path = Path(args.db) if args.db else defaults.state_db_path

    score = AgentOutcomeScore(
        run_id=args.run_id,
        work_item_id=args.work_item,
        role=args.role,
        passed_stop_conditions=not args.failed_stop_conditions,
        scope_respected=not args.scope_violated,
        tests_green=not args.tests_red,
        review_rounds=args.review_rounds,
        human_override=args.human_override,
        notes=args.notes,
    )

    saved = record_agent_outcome_score(db_path, score)
    print(
        json.dumps(
            {
                "recorded": True,
                "score_id": saved.score_id,
                "run_id": saved.run_id,
                "work_item_id": saved.work_item_id,
                "role": saved.role,
                "passed_stop_conditions": saved.passed_stop_conditions,
                "scope_respected": saved.scope_respected,
                "tests_green": saved.tests_green,
                "review_rounds": saved.review_rounds,
                "human_override": saved.human_override,
                "notes": saved.notes,
                "scored_at": saved.scored_at,
                "db_path": str(db_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

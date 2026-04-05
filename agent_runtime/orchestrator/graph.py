"""First orchestration entrypoint for the repository delivery relay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .state import RuntimeSnapshot
from .simulations import build_simulation_snapshot, simulation_names
from .transitions import decide_next_action
from .work_item_registry import load_work_items


def build_runtime_snapshot(repo_root: Path) -> RuntimeSnapshot:
    return RuntimeSnapshot(work_items=load_work_items(repo_root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the repository agent runtime.")
    parser.add_argument(
        "--simulate",
        choices=simulation_names(),
        help="Run a built-in simulation scenario instead of reading the live repository state.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List the built-in simulation scenarios and exit.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_scenarios:
        print(json.dumps({"simulation_scenarios": simulation_names()}, indent=2))
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    snapshot = (
        build_simulation_snapshot(args.simulate)
        if args.simulate is not None
        else build_runtime_snapshot(repo_root)
    )
    decision = decide_next_action(snapshot)
    print(
        json.dumps(
            {
                "action": decision.action.value,
                "simulation": args.simulate,
                "work_item_id": decision.work_item_id,
                "reason": decision.reason,
                "target_path": str(decision.target_path) if decision.target_path else None,
                "metadata": decision.metadata,
                "work_item_count": len(snapshot.work_items),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0

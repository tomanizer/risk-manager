"""First orchestration entrypoint for the repository delivery relay."""

from __future__ import annotations

import json
from pathlib import Path

from .state import RuntimeSnapshot
from .transitions import decide_next_action
from .work_item_registry import load_work_items


def build_runtime_snapshot(repo_root: Path) -> RuntimeSnapshot:
    return RuntimeSnapshot(work_items=load_work_items(repo_root))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    snapshot = build_runtime_snapshot(repo_root)
    decision = decide_next_action(snapshot)
    print(
        json.dumps(
            {
                "action": decision.action.value,
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

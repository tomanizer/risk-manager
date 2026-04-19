#!/usr/bin/env python3
"""Run the daily risk investigation orchestrator against built-in fixture scenarios.

Usage:
    python scripts/run_daily_risk_investigation.py
    python scripts/run_daily_risk_investigation.py --scenario missing-node-exclusion
    python scripts/run_daily_risk_investigation.py --format json

This helper is intentionally fixture-backed. It mirrors the main integration
scenarios so the orchestrator slice can be stepped through in a debugger
without rebuilding typed inputs by hand.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.modules.controls_integrity.fixtures import ControlsIntegrityFixtureIndex
    from src.modules.risk_analytics.contracts import MeasureType, NodeRef
    from src.modules.risk_analytics.fixtures import FixtureIndex
    from src.orchestrators.daily_risk_investigation import DailyRunResult


@dataclass(frozen=True)
class RuntimeSurfaces:
    build_controls_integrity_fixture_index: Callable[..., "ControlsIntegrityFixtureIndex"]
    hierarchy_scope: Any
    measure_type: type["MeasureType"]
    node_level: Any
    node_ref: type["NodeRef"]
    build_fixture_index: Callable[..., "FixtureIndex"]
    start_daily_run: Callable[..., "DailyRunResult"]
    configure_operation_logging: Callable[..., None]


def find_repo_root(start: Path) -> Path:
    candidate = start if start.is_dir() else start.parent
    for path in (candidate, *candidate.parents):
        if (path / "AGENTS.md").exists() and (path / "work_items").is_dir():
            return path
    raise RuntimeError("Could not find repository root.")


def _bootstrap_repo_imports() -> None:
    repo_root = find_repo_root(Path.cwd())
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


@lru_cache(maxsize=1)
def _load_runtime_surfaces() -> RuntimeSurfaces:
    _bootstrap_repo_imports()
    from src.modules.controls_integrity.fixtures import build_controls_integrity_fixture_index
    from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
    from src.modules.risk_analytics.fixtures import build_fixture_index
    from src.orchestrators.daily_risk_investigation import start_daily_run
    from src.shared.telemetry import configure_operation_logging

    return RuntimeSurfaces(
        build_controls_integrity_fixture_index=build_controls_integrity_fixture_index,
        hierarchy_scope=HierarchyScope,
        measure_type=MeasureType,
        node_level=NodeLevel,
        node_ref=NodeRef,
        build_fixture_index=build_fixture_index,
        start_daily_run=start_daily_run,
        configure_operation_logging=configure_operation_logging,
    )


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    as_of_date: date
    snapshot_id: str
    candidate_targets: tuple["NodeRef", ...]
    measure_type: "MeasureType"


def _firm_grp() -> "NodeRef":
    surfaces = _load_runtime_surfaces()
    return surfaces.node_ref(
        hierarchy_scope=surfaces.hierarchy_scope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=surfaces.node_level.FIRM,
        node_id="FIRM_GRP",
    )


def _division_toh() -> "NodeRef":
    surfaces = _load_runtime_surfaces()
    return surfaces.node_ref(
        hierarchy_scope=surfaces.hierarchy_scope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=surfaces.node_level.DIVISION,
        node_id="DIV_GM",
    )


def _division_le_uk() -> "NodeRef":
    surfaces = _load_runtime_surfaces()
    return surfaces.node_ref(
        hierarchy_scope=surfaces.hierarchy_scope.LEGAL_ENTITY,
        legal_entity_id="LE-UK-BANK",
        node_level=surfaces.node_level.DIVISION,
        node_id="DIV_GM",
    )


def _book_new_issues() -> "NodeRef":
    surfaces = _load_runtime_surfaces()
    return surfaces.node_ref(
        hierarchy_scope=surfaces.hierarchy_scope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=surfaces.node_level.BOOK,
        node_id="BOOK_NEW_ISSUES",
    )


def build_scenarios() -> dict[str, Scenario]:
    surfaces = _load_runtime_surfaces()
    return {
        "happy-path": Scenario(
            name="happy-path",
            description="Two valid top-of-house targets; expected to complete without service errors.",
            as_of_date=date(2026, 1, 2),
            snapshot_id="SNAP-2026-01-02",
            candidate_targets=(_firm_grp(), _division_toh()),
            measure_type=surfaces.measure_type.VAR_1D_99,
        ),
        "missing-node-exclusion": Scenario(
            name="missing-node-exclusion",
            description="One legal-entity candidate is missing in the pinned top-of-house snapshot and is filtered out at Stage 3.",
            as_of_date=date(2026, 1, 2),
            snapshot_id="SNAP-2026-01-02",
            candidate_targets=(_firm_grp(), _division_le_uk(), _division_toh()),
            measure_type=surfaces.measure_type.VAR_1D_99,
        ),
        "blocked-readiness": Scenario(
            name="blocked-readiness",
            description="Readiness canary hits MISSING_SNAPSHOT and the run short-circuits before target selection.",
            as_of_date=date(2026, 1, 2),
            snapshot_id="SNAP-DOES-NOT-EXIST-IN-FIXTURE",
            candidate_targets=(_firm_grp(), _division_toh()),
            measure_type=surfaces.measure_type.VAR_1D_99,
        ),
        "hold-investigation-failed": Scenario(
            name="hold-investigation-failed",
            description="Selection passes, but one target returns MISSING_CONTROL_CONTEXT and is held at Stage 7.",
            as_of_date=date(2026, 1, 8),
            snapshot_id="SNAP-2026-01-08",
            candidate_targets=(_division_toh(), _book_new_issues()),
            measure_type=surfaces.measure_type.VAR_1D_99,
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the daily risk investigation orchestrator against fixture-backed scenarios.")
    parser.add_argument(
        "--scenario",
        choices=sorted(build_scenarios()),
        default="happy-path",
        help="Named orchestrator scenario to run.",
    )
    parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary).",
    )
    parser.add_argument(
        "--emit-telemetry",
        action="store_true",
        help="Emit operation-log events while the scenario runs.",
    )
    return parser.parse_args()


def run_scenario(name: str) -> tuple[Scenario, "DailyRunResult"]:
    scenarios = build_scenarios()
    scenario = scenarios[name]
    surfaces = _load_runtime_surfaces()
    risk_index = surfaces.build_fixture_index()
    controls_index = surfaces.build_controls_integrity_fixture_index()
    result = surfaces.start_daily_run(
        as_of_date=scenario.as_of_date,
        snapshot_id=scenario.snapshot_id,
        candidate_targets=scenario.candidate_targets,
        measure_type=scenario.measure_type,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    return scenario, result


def _summary_payload(scenario: Scenario, result: "DailyRunResult") -> dict[str, object]:
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "as_of_date": scenario.as_of_date.isoformat(),
        "snapshot_id": scenario.snapshot_id,
        "measure_type": scenario.measure_type.value,
        "candidate_node_ids": [node.node_id for node in scenario.candidate_targets],
        "selected_node_ids": [node.node_id for node in result.selected_targets],
        "readiness_state": result.readiness_state.value,
        "readiness_reason_codes": list(result.readiness_reason_codes),
        "terminal_status": result.terminal_status.value,
        "degraded": result.degraded,
        "partial": result.partial,
        "run_id": result.run_id,
        "handoff": [
            {
                "node_id": entry.node_ref.node_id,
                "handoff_status": entry.handoff_status.value,
                "blocking_reason_codes": [code.value for code in entry.blocking_reason_codes],
                "cautionary_reason_codes": [code.value for code in entry.cautionary_reason_codes],
                "service_error_status_code": entry.service_error_status_code,
            }
            for entry in result.handoff
        ],
    }


def main() -> int:
    args = parse_args()
    surfaces = _load_runtime_surfaces()
    if not args.emit_telemetry:
        surfaces.configure_operation_logging(enabled=False)
    scenario, result = run_scenario(args.scenario)
    if args.format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(json.dumps(_summary_payload(scenario, result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

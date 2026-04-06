from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.architecture_boundaries import build_architecture_boundary_report


def test_architecture_boundary_report_detects_module_importing_walker(tmp_path: Path) -> None:
    _write_boundary_repo(tmp_path)
    module_file = tmp_path / "src" / "modules" / "risk_analytics" / "service.py"
    module_file.write_text("from src.walkers.quant import Walker\n", encoding="utf-8")

    report = build_architecture_boundary_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "module_imports_walker_surface"
    assert finding.import_target == "src.walkers.quant"


def test_architecture_boundary_report_detects_walker_importing_orchestrator(tmp_path: Path) -> None:
    _write_boundary_repo(tmp_path)
    walker_file = tmp_path / "src" / "walkers" / "quant.py"
    walker_file.parent.mkdir(parents=True, exist_ok=True)
    walker_file.write_text("from src.orchestrators.daily import run_daily\n", encoding="utf-8")

    report = build_architecture_boundary_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "walker_imports_orchestrator_surface"
    assert finding.import_target == "src.orchestrators.daily"


def test_architecture_boundary_report_detects_runtime_importing_module(tmp_path: Path) -> None:
    _write_boundary_repo(tmp_path)
    runtime_file = tmp_path / "agent_runtime" / "runner.py"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text("from src.modules.risk_analytics.service import get_risk_history\n", encoding="utf-8")

    report = build_architecture_boundary_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "runtime_imports_module_surface"
    assert finding.import_target == "src.modules.risk_analytics.service"


def test_architecture_boundary_report_allows_internal_relative_imports(tmp_path: Path) -> None:
    _write_boundary_repo(tmp_path)

    report = build_architecture_boundary_report(tmp_path)

    assert report.findings == ()


def test_check_architecture_boundaries_cli_writes_json_report(tmp_path: Path) -> None:
    _write_boundary_repo(tmp_path)
    output_path = tmp_path / "artifacts" / "drift" / "architecture_boundaries.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_architecture_boundaries.py",
            "--root",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["scan_name"] == "architecture_boundaries"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0


def test_repo_architecture_boundary_scan_has_no_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_architecture_boundary_report(repo_root)

    assert report.findings == ()


def _write_boundary_repo(root: Path) -> None:
    module_root = root / "src" / "modules" / "risk_analytics"
    module_root.mkdir(parents=True, exist_ok=True)
    module_root.joinpath("__init__.py").write_text("from .service import get_risk_history\n", encoding="utf-8")
    module_root.joinpath("service.py").write_text("from .contracts import Contract\n", encoding="utf-8")
    module_root.joinpath("contracts.py").write_text("class Contract: ...\n", encoding="utf-8")

    walker_root = root / "src" / "walkers"
    walker_root.mkdir(parents=True, exist_ok=True)
    walker_root.joinpath("__init__.py").write_text("", encoding="utf-8")

    orchestrator_root = root / "src" / "orchestrators"
    orchestrator_root.mkdir(parents=True, exist_ok=True)
    orchestrator_root.joinpath("__init__.py").write_text("", encoding="utf-8")

    runtime_root = root / "agent_runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_root.joinpath("__init__.py").write_text("", encoding="utf-8")

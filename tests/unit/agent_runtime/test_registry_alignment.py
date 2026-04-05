from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.registry_alignment import build_registry_alignment_report


def test_registry_alignment_reports_missing_implemented_paths(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress
              contract_status: implemented
              sub_components:
                - name: history_service
                  path: src/modules/risk_analytics/service.py
                  status: implemented
        """,
    )
    (tmp_path / "src" / "modules" / "risk_analytics").mkdir(parents=True)

    report = build_registry_alignment_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_registered_path"
    assert finding.component_id == "MOD-RISK-ANALYTICS"
    assert finding.implementation_path == "src/modules/risk_analytics/service.py"
    assert finding.severity == "critical"


def test_registry_alignment_reports_unexpected_paths_for_not_started_subcomponents(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress
              contract_status: implemented
              sub_components:
                - name: risk_summary_core_service
                  path: src/modules/risk_analytics/core.py
                  status: not-started
        """,
    )
    core_path = tmp_path / "src" / "modules" / "risk_analytics" / "core.py"
    core_path.parent.mkdir(parents=True)
    core_path.write_text("pass\n", encoding="utf-8")

    report = build_registry_alignment_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "unexpected_implemented_path"
    assert finding.component_name == "risk_summary_core_service"
    assert finding.severity == "critical"


def test_registry_alignment_reports_implemented_subcomponents_without_paths(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress
              contract_status: implemented
              sub_components:
                - name: fixture_loader
                  path: null
                  status: implemented
        """,
    )
    (tmp_path / "src" / "modules" / "risk_analytics").mkdir(parents=True)

    report = build_registry_alignment_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "implemented_subcomponent_without_path"
    assert finding.implementation_path is None
    assert finding.severity == "critical"


def test_registry_alignment_reports_unregistered_module_roots(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress
              contract_status: implemented
        """,
    )
    (tmp_path / "src" / "modules" / "risk_analytics").mkdir(parents=True)
    (tmp_path / "src" / "modules" / "limits_approvals").mkdir(parents=True)

    report = build_registry_alignment_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "unregistered_module_root"
    assert finding.implementation_path == "src/modules/limits_approvals"
    assert finding.severity == "critical"
    assert report.stats.components_scanned == 1


def test_registry_alignment_uses_component_id_for_module_root_mapping(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics (Renamed Display Label)
              status: in-progress
              contract_status: implemented
        """,
    )
    (tmp_path / "src" / "modules" / "risk_analytics").mkdir(parents=True)

    report = build_registry_alignment_report(tmp_path)

    assert report.findings == ()
    assert report.stats.components_scanned == 1


def test_registry_alignment_counts_only_module_components_as_scanned(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress
              contract_status: implemented
          walkers:
            - id: WALKER-QUANT
              name: Quant Walker
              status: proposed
              contract_status: draft
        """,
    )
    (tmp_path / "src" / "modules" / "risk_analytics").mkdir(parents=True)

    report = build_registry_alignment_report(tmp_path)

    assert report.findings == ()
    assert report.stats.components_scanned == 1


def test_registry_alignment_supports_trailing_yaml_comments(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules: # active section
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress # implemented foundation
              contract_status: implemented
              sub_components: # tracked paths
                - name: history_service
                  path: src/modules/risk_analytics/service.py # deterministic service
                  status: implemented
        """,
    )
    service_path = tmp_path / "src" / "modules" / "risk_analytics" / "service.py"
    service_path.parent.mkdir(parents=True)
    service_path.write_text("pass\n", encoding="utf-8")

    report = build_registry_alignment_report(tmp_path)

    assert report.findings == ()


def test_check_registry_alignment_cli_writes_json_report(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        """
        version: 1
        components:
          modules:
            - id: MOD-RISK-ANALYTICS
              name: Risk Analytics
              status: in-progress
              contract_status: implemented
        """,
    )
    (tmp_path / "src" / "modules" / "risk_analytics").mkdir(parents=True)
    output_path = tmp_path / "artifacts" / "drift" / "registry_alignment.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_registry_alignment.py",
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

    assert payload["scan_name"] == "registry_alignment"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0
    assert payload["stats"]["components_scanned"] == 1


def test_repo_registry_alignment_scan_has_no_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_registry_alignment_report(repo_root)

    assert report.findings == ()


def _write_registry(root: Path, content: str) -> None:
    registry_path = root / "docs" / "registry" / "current_state_registry.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(_dedent(content), encoding="utf-8")


def _dedent(content: str) -> str:
    lines = [line.rstrip() for line in content.strip().splitlines()]
    min_indent = min(len(line) - len(line.lstrip(" ")) for line in lines if line)
    return "\n".join(line[min_indent:] for line in lines) + "\n"

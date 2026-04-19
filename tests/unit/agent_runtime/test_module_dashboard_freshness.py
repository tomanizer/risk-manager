from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.module_dashboard_freshness import build_module_dashboard_freshness_report
from scripts.render_module_dashboard import load_registry, render_module_dashboard


def test_module_dashboard_freshness_reports_no_findings_when_synced(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path)
    payload = load_registry(registry_path)
    dashboard_path = tmp_path / "docs" / "roadmap" / "module_1_var_dashboard.md"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(render_module_dashboard(payload, module_id="MODULE-1-VAR"), encoding="utf-8")

    report = build_module_dashboard_freshness_report(tmp_path)

    assert report.stats.dashboards_declared == 1
    assert report.stats.dashboards_checked == 1
    assert report.stats.findings_count == 0
    assert report.findings == ()


def test_module_dashboard_freshness_reports_missing_dashboard(tmp_path: Path) -> None:
    _write_registry(tmp_path)

    report = build_module_dashboard_freshness_report(tmp_path)

    assert report.stats.findings_count == 1
    assert report.stats.missing_dashboards == 1
    finding = report.findings[0]
    assert finding.kind == "missing_generated_dashboard"
    assert finding.dashboard_path == "docs/roadmap/module_1_var_dashboard.md"
    assert "render_module_dashboard.py --module-id MODULE-1-VAR" in finding.message


def test_module_dashboard_freshness_reports_stale_dashboard(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    dashboard_path = tmp_path / "docs" / "roadmap" / "module_1_var_dashboard.md"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text("# stale\n", encoding="utf-8")

    report = build_module_dashboard_freshness_report(tmp_path)

    assert report.stats.findings_count == 1
    assert report.stats.stale_dashboards == 1
    finding = report.findings[0]
    assert finding.kind == "stale_generated_dashboard"
    assert finding.dashboard_path == "docs/roadmap/module_1_var_dashboard.md"


def test_check_module_dashboard_freshness_cli_writes_json_report(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    output_path = tmp_path / "artifacts" / "drift" / "module_dashboard_freshness.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_module_dashboard_freshness.py",
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

    assert payload["scan_name"] == "module_dashboard_freshness"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 1


def _write_registry(root: Path) -> Path:
    registry_path = root / "docs" / "registry" / "current_state_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "\n".join(
            [
                "version: 2",
                "last_updated: 2026-04-19",
                "module_dashboards:",
                "  - id: MODULE-1-VAR",
                '    name: "Module 1 Dashboard: End-to-End VaR Workflow"',
                "    owner_role: PM",
                "    dashboard_path: docs/roadmap/module_1_var_dashboard.md",
                "    overall_state: MVP_PARTIAL",
                "    delivery_phase: Phase 5",
                "    mission: Test mission.",
                "    mvp_definition:",
                "      - deterministic analysis",
                "    summary: Test summary.",
                "    current_mvp_blockers:",
                "      - Test blocker.",
                "    not_required_for_mvp:",
                "      - Test enhancement.",
                "    journey_stages: []",
                "    capabilities: []",
                "    prd_lineage: []",
                "    in_progress_items: []",
                "    next_recommended_slices:",
                "      - Next slice.",
                "    post_mvp_enhancements:",
                "      - Post MVP.",
                "    open_questions:",
                "      - Open question?",
                "    change_log:",
                '      - "2026-04-19: Seeded dashboard."',
                "components:",
                "  modules: []",
                "  walkers: []",
                "  orchestrators: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return registry_path

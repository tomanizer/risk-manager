from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.instruction_surfaces import build_instruction_surface_report
from tests.unit.agent_runtime.test_drift_suite import _write_instruction_surfaces


def test_instruction_surface_report_detects_missing_role_pair(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    (tmp_path / "prompts" / "agents" / "review_agent_instruction.md").unlink()

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_instruction_surface"
    assert finding.related_paths == ("prompts/agents/review_agent_instruction.md",)


def test_instruction_surface_report_detects_readme_inventory_drift(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    readme_path = tmp_path / ".github" / "agents" / "README.md"
    readme_path.write_text("- `pm.agent.md`\n", encoding="utf-8")

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "instruction_inventory_drift"
    assert finding.source_path == ".github/agents/README.md"


def test_instruction_surface_report_detects_missing_agents_reference(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    claude_path = tmp_path / "CLAUDE.md"
    claude_path.write_text(
        "\n".join(
            [
                "1. git fetch origin",
                "2. git switch main",
                "3. git pull --ff-only origin main",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_agents_reference"
    assert finding.source_path == "CLAUDE.md"


def test_instruction_surface_report_detects_incomplete_freshness_rule(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    review_path = tmp_path / ".github" / "agents" / "review.agent.md"
    review_path.write_text("Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n", encoding="utf-8")

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "incomplete_freshness_rule"
    assert finding.source_path == ".github/agents/review.agent.md"
    assert finding.related_paths == ("git pull --ff-only origin main",)


def test_instruction_surface_report_detects_missing_drift_suite_entrypoint(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    drift_prompt = tmp_path / "prompts" / "drift_monitor" / "repo_health_audit_prompt.md"
    drift_prompt.write_text("Run the drift monitor.\n", encoding="utf-8")

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_drift_suite_entrypoint"
    assert finding.source_path == "prompts/drift_monitor/repo_health_audit_prompt.md"


def test_check_instruction_surfaces_cli_writes_json_report(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    output_path = tmp_path / "artifacts" / "drift" / "instruction_surfaces.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_instruction_surfaces.py",
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

    assert payload["scan_name"] == "instruction_surfaces"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0


def test_repo_instruction_surface_scan_has_no_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_instruction_surface_report(repo_root)

    assert report.findings == ()

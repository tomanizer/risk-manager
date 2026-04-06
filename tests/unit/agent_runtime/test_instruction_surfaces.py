from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.instruction_surfaces import build_instruction_surface_report


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


def test_instruction_surface_report_detects_stale_readme_inventory_entries(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    readme_path = tmp_path / ".github" / "agents" / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "- `pm.agent.md`",
                "- `prd-spec.agent.md`",
                "- `issue-planner.agent.md`",
                "- `risk-methodology-spec.agent.md`",
                "- `coding.agent.md`",
                "- `review.agent.md`",
                "- `drift-monitor.agent.md`",
                "- `legacy.agent.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "instruction_inventory_drift"
    assert finding.source_path == ".github/agents/README.md"
    assert finding.related_paths == ("legacy.agent.md",)


def test_instruction_surface_report_detects_missing_agents_reference(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    prompt_path = tmp_path / "prompts" / "agents" / "pm_agent_instruction.md"
    prompt_path.write_text("# PM\n", encoding="utf-8")

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_agents_reference"
    assert finding.source_path == "prompts/agents/pm_agent_instruction.md"


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


def test_instruction_surface_report_detects_incomplete_prompt_freshness_rule(tmp_path: Path) -> None:
    _write_instruction_surfaces(tmp_path)
    prompt_path = tmp_path / "prompts" / "agents" / "review_agent_instruction.md"
    prompt_path.write_text("Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n", encoding="utf-8")

    report = build_instruction_surface_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "incomplete_freshness_rule"
    assert finding.source_path == "prompts/agents/review_agent_instruction.md"
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


def _write_instruction_surfaces(root: Path) -> None:
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text(
        "\n".join(
            [
                "Read `AGENTS.md` first.",
                "1. git fetch origin",
                "2. git switch main",
                "3. git pull --ff-only origin main",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "GEMINI.md").write_text(
        "\n".join(
            [
                "Read `AGENTS.md` first.",
                "1. git fetch origin",
                "2. git switch main",
                "3. git pull --ff-only origin main",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    copilot_path = root / ".github" / "copilot-instructions.md"
    copilot_path.parent.mkdir(parents=True, exist_ok=True)
    copilot_path.write_text("# Copilot\n", encoding="utf-8")
    (root / "docs" / "guides").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "guides" / "overnight_agent_runbook.md").write_text(
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
    github_agents_dir = root / ".github" / "agents"
    github_agents_dir.mkdir(parents=True, exist_ok=True)
    (github_agents_dir / "README.md").write_text(
        "\n".join(
            [
                "- `pm.agent.md`",
                "- `prd-spec.agent.md`",
                "- `issue-planner.agent.md`",
                "- `risk-methodology-spec.agent.md`",
                "- `coding.agent.md`",
                "- `review.agent.md`",
                "- `drift-monitor.agent.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    prompt_agents_dir = root / "prompts" / "agents"
    prompt_agents_dir.mkdir(parents=True, exist_ok=True)
    (prompt_agents_dir / "README.md").write_text(
        "\n".join(
            [
                "- `pm_agent_instruction.md`",
                "- `prd_spec_agent_instruction.md`",
                "- `coding_agent_instruction.md`",
                "- `review_agent_instruction.md`",
                "- `issue_planner_instruction.md`",
                "- `risk_methodology_spec_agent_instruction.md`",
                "- `drift_monitor_agent_instruction.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    prompt_drift_dir = root / "prompts" / "drift_monitor"
    prompt_drift_dir.mkdir(parents=True, exist_ok=True)
    script_dir = root / "scripts" / "drift"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_dir.joinpath("run_all.py").write_text("print('drift')\n", encoding="utf-8")
    prompt_drift_dir.joinpath("repo_health_audit_prompt.md").write_text(
        "Use `python scripts/drift/run_all.py --root . --artifact-dir artifacts/drift --output artifacts/drift/latest_report.json --summary-output artifacts/drift/summary.md`.\n",
        encoding="utf-8",
    )

    github_agent_contents = {
        "coding.agent.md": "Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n3. `git pull --ff-only origin main`\n",
        "drift-monitor.agent.md": "Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n3. `git pull --ff-only origin main`\nUse `scripts/drift/run_all.py`.\n",
        "issue-planner.agent.md": "Read `AGENTS.md`.\n",
        "pm.agent.md": "Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n3. `git pull --ff-only origin main`\n",
        "prd-spec.agent.md": "Read `AGENTS.md`.\n",
        "review.agent.md": "Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n3. `git pull --ff-only origin main`\n",
        "risk-methodology-spec.agent.md": "Read `AGENTS.md`.\n",
    }
    for filename, content in github_agent_contents.items():
        (github_agents_dir / filename).write_text(content, encoding="utf-8")

    prompt_agent_contents = {
        "coding_agent_instruction.md": "Read `AGENTS.md`.\n# Coding\n",
        "drift_monitor_agent_instruction.md": "Read `AGENTS.md`.\nUse `scripts/drift/run_all.py`.\n",
        "issue_planner_instruction.md": "Read `AGENTS.md`.\n# Issue planner\n",
        "pm_agent_instruction.md": "Read `AGENTS.md`.\n# PM\n",
        "prd_spec_agent_instruction.md": "Read `AGENTS.md`.\n# PRD Spec\n",
        "review_agent_instruction.md": "Read `AGENTS.md`.\n# Review\n",
        "risk_methodology_spec_agent_instruction.md": "Read `AGENTS.md`.\n",
    }
    for filename, content in prompt_agent_contents.items():
        (prompt_agents_dir / filename).write_text(content, encoding="utf-8")

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.drift_suite import build_drift_suite_report, render_drift_suite_issue_body


def test_drift_suite_waives_findings_present_in_baseline(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    initial_report = build_drift_suite_report(tmp_path)

    assert initial_report.stats.scans_run == 4
    assert initial_report.stats.total_findings == 1
    assert initial_report.stats.new_findings == 1
    assert initial_report.stats.waived_findings == 0
    assert initial_report.findings[0].scan_name == "reference_integrity"

    baseline_path = tmp_path / "artifacts" / "drift" / "baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(
            {
                "version": 1,
                "allowed_findings": [
                    {
                        "scan_name": initial_report.findings[0].scan_name,
                        "signature": initial_report.findings[0].signature,
                        "rationale": "Known planned follow-up.",
                        "issue": "#999",
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    baselined_report = build_drift_suite_report(tmp_path, baseline_path=baseline_path)

    assert baselined_report.stats.total_findings == 1
    assert baselined_report.stats.new_findings == 0
    assert baselined_report.stats.waived_findings == 1
    assert baselined_report.findings == ()
    waived = baselined_report.waived_findings[0]
    assert waived.rationale == "Known planned follow-up."
    assert waived.issue == "#999"
    scan_summary = next(scan for scan in baselined_report.scans if scan.scan_name == "reference_integrity")
    assert scan_summary.total_findings == 1
    assert len(scan_summary.new_findings) == 0
    assert len(scan_summary.waived_findings) == 1


def test_run_all_cli_writes_combined_and_per_scanner_artifacts(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    artifact_dir = tmp_path / "artifacts" / "drift"
    output_path = artifact_dir / "latest_report.json"
    summary_path = artifact_dir / "summary.md"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/run_all.py",
            "--root",
            str(tmp_path),
            "--artifact-dir",
            str(artifact_dir),
            "--output",
            str(output_path),
            "--summary-output",
            str(summary_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["scan_name"] == "drift_suite"
    assert payload == written_payload
    assert payload["stats"]["scans_run"] == 4
    assert payload["stats"]["new_findings"] == 1
    assert (artifact_dir / "dependency_hygiene.json").is_file()
    assert (artifact_dir / "instruction_surfaces.json").is_file()
    assert (artifact_dir / "reference_integrity.json").is_file()
    assert (artifact_dir / "registry_alignment.json").is_file()
    summary = summary_path.read_text(encoding="utf-8")
    assert "## Drift Monitor" in summary
    assert "### Instruction Surfaces" in summary
    assert "### Reference Integrity" in summary


def test_run_all_cli_uses_baseline_for_fail_on_findings(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    artifact_dir = tmp_path.parent / "drift-artifacts"
    output_path = artifact_dir / "latest_report.json"
    summary_path = artifact_dir / "summary.md"
    unwaived = subprocess.run(
        [
            sys.executable,
            "scripts/drift/run_all.py",
            "--root",
            str(tmp_path),
            "--artifact-dir",
            str(artifact_dir),
            "--output",
            str(output_path),
            "--summary-output",
            str(summary_path),
            "--fail-on-findings",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert unwaived.returncode == 1

    initial_payload = json.loads(unwaived.stdout)
    baseline_path = tmp_path / "artifacts" / "drift" / "baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(
            {
                "version": 1,
                "allowed_findings": [
                    {
                        "scan_name": initial_payload["findings"][0]["scan_name"],
                        "signature": initial_payload["findings"][0]["signature"],
                        "rationale": "Tracked drift.",
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    waived = subprocess.run(
        [
            sys.executable,
            "scripts/drift/run_all.py",
            "--root",
            str(tmp_path),
            "--baseline",
            str(baseline_path),
            "--artifact-dir",
            str(artifact_dir),
            "--output",
            str(output_path),
            "--summary-output",
            str(summary_path),
            "--fail-on-findings",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
        capture_output=True,
        text=True,
    )

    assert waived.returncode == 0
    payload = json.loads(waived.stdout)
    assert payload["stats"]["new_findings"] == 0
    assert payload["stats"]["waived_findings"] == 1


def test_render_drift_suite_issue_body_includes_marker_and_findings(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)

    report = build_drift_suite_report(tmp_path)
    body = render_drift_suite_issue_body(report)

    assert "<!-- drift-monitor-issue -->" in body
    assert "# Repo Health Drift Report" in body
    assert "## Net-New Findings" in body
    assert "reference_integrity: missing_reference" in body
    assert "README.md:1 `docs/missing.md`" in body


def test_repo_drift_suite_has_no_new_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_drift_suite_report(repo_root)

    assert report.findings == ()


def _write_minimal_repo(root: Path) -> None:
    (root / "README.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "risk-manager"',
                'version = "0.0.0"',
                'requires-python = ">=3.12"',
                'dependencies = ["pydantic>=2.0,<3.0"]',
                "",
                "[project.optional-dependencies]",
                'dev = ["pytest==9.0.2", "ruff==0.15.9", "mypy"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("import pydantic\n", encoding="utf-8")
    workflow = root / ".github" / "workflows" / "drift-monitor.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "name: drift\njobs:\n  audit:\n    steps:\n      - run: pytest -q\n      - run: ruff check .\n      - run: mypy src/\n",
        encoding="utf-8",
    )
    registry = root / "docs" / "registry" / "current_state_registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "\n".join(
            [
                "modules:",
                "  - id: module-risk-summary",
                "    name: Risk Summary",
                "    status: draft",
                "    contract_status: draft",
                "walkers:",
                "orchestrators:",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_instruction_surfaces(root)


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
        "review.agent.md": "Read `AGENTS.md`.\n1. `git fetch origin`\n2. `git switch main`\n3. `git pull --ff-only origin main`\n",
        "risk-methodology-spec.agent.md": "Read `AGENTS.md`.\n",
    }
    for filename, content in github_agent_contents.items():
        (github_agents_dir / filename).write_text(content, encoding="utf-8")

    prompt_agent_contents = {
        "coding_agent_instruction.md": "# Coding\n",
        "drift_monitor_agent_instruction.md": "Use `scripts/drift/run_all.py`.\n",
        "issue_planner_instruction.md": "# Issue planner\n",
        "pm_agent_instruction.md": "# PM\n",
        "review_agent_instruction.md": "# Review\n",
        "risk_methodology_spec_agent_instruction.md": "Read `AGENTS.md`.\n",
    }
    for filename, content in prompt_agent_contents.items():
        (prompt_agents_dir / filename).write_text(content, encoding="utf-8")

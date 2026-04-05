from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.reference_integrity import build_reference_scan_report


def test_reference_scan_reports_missing_internal_paths(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (docs_dir / "existing.md").write_text("# existing\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "\n".join(
            [
                "# Guide",
                "See `docs/existing.md`.",
                "See `docs/missing.md`.",
                "See [prompt](../README.md).",
                "Ignore [external](https://example.com/docs/missing.md).",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_reference_scan_report(tmp_path)

    assert report.stats.files_scanned == 3
    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.source_file == "docs/guide.md"
    assert finding.source_line == 3
    assert finding.reference == "docs/missing.md"
    assert finding.drift_class == "canon drift"
    assert finding.owner == "PM"


def test_reference_scan_classifies_prompt_refs_as_operational_instruction_drift(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent.md").write_text("Read `docs/does-not-exist.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.drift_class == "operational-instruction drift"
    assert finding.owner == "PM"


def test_reference_scan_reports_escaping_paths(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("See `../../outside.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.reference == "../../outside.md"
    assert "escapes the repository root" in finding.message


def test_check_references_cli_writes_json_report(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")
    output_path = tmp_path / "artifacts" / "drift" / "reference_integrity.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_references.py",
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

    assert payload["scan_name"] == "reference_integrity"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 1


def test_repo_scan_has_no_missing_test_layout_references() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_reference_scan_report(repo_root)

    blocked_findings = {
        ("tests/README.md", "tests/integration/"),
        ("tests/README.md", "tests/replay/"),
        ("tests/README.md", "tests/golden_cases/"),
        ("work_items/ready/WI-1.1.4-risk-summary-core-service.md", "tests/replay/"),
        ("work_items/ready/WI-1.1.5-risk-summary-rolling-stats-and-replay.md", "tests/replay/"),
    }

    unexpected = {
        (finding.source_file, finding.reference)
        for finding in report.findings
        if (finding.source_file, finding.reference) in blocked_findings
    }

    assert unexpected == set()

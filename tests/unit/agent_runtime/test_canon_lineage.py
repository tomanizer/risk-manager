from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.canon_lineage import build_canon_lineage_report


def test_canon_lineage_report_detects_multiple_active_versions(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    active_v1 = tmp_path / "docs" / "prds" / "phase-1" / "PRD-1.1-example-v1.md"
    active_v1.write_text("# PRD Example v1\n", encoding="utf-8")

    report = build_canon_lineage_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "multiple_active_versions"
    assert finding.related_paths == (
        "docs/prds/phase-1/PRD-1.1-example-v1.md",
        "docs/prds/phase-1/PRD-1.1-example-v2.md",
    )


def test_canon_lineage_report_detects_missing_supersedes_reference(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    active_v2 = tmp_path / "docs" / "prds" / "phase-1" / "PRD-1.1-example-v2.md"
    active_v2.write_text("# PRD Example v2\n", encoding="utf-8")

    report = build_canon_lineage_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_supersedes_reference"
    assert finding.source_path == "docs/prds/phase-1/PRD-1.1-example-v2.md"


def test_canon_lineage_report_detects_mismatched_supersedes_reference(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    archive_dir = tmp_path / "docs" / "prds" / "phase-1" / "archive"
    archive_dir.joinpath("PRD-1.1-other-v1-archived.md").write_text("# Other v1\n", encoding="utf-8")
    active_v2 = tmp_path / "docs" / "prds" / "phase-1" / "PRD-1.1-example-v2.md"
    active_v2.write_text(
        "- **Supersedes:** `archive/PRD-1.1-other-v1-archived.md`\n",
        encoding="utf-8",
    )

    report = build_canon_lineage_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "mismatched_supersedes_reference"
    assert finding.related_paths == ("archive/PRD-1.1-other-v1-archived.md",)


def test_canon_lineage_report_detects_archived_canon_reference_in_active_surface(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    work_item = tmp_path / "work_items" / "ready" / "WI-1.md"
    work_item.parent.mkdir(parents=True, exist_ok=True)
    work_item.write_text(
        "See `docs/prds/phase-1/archive/PRD-1.1-example-v1-archived.md`.\n",
        encoding="utf-8",
    )

    report = build_canon_lineage_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "archived_canon_reference_in_active_surface"
    assert finding.source_path == "work_items/ready/WI-1.md"


def test_canon_lineage_report_detects_relative_parent_archived_reference(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    work_item = tmp_path / "work_items" / "ready" / "WI-1.md"
    work_item.parent.mkdir(parents=True, exist_ok=True)
    work_item.write_text(
        "See `../../docs/prds/phase-1/archive/PRD-1.1-example-v1-archived.md`.\n",
        encoding="utf-8",
    )

    report = build_canon_lineage_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "archived_canon_reference_in_active_surface"
    assert finding.related_paths == ("../../docs/prds/phase-1/archive/PRD-1.1-example-v1-archived.md",)


def test_canon_lineage_report_detects_suffix_archived_reference(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    suffix_archived = tmp_path / "docs" / "prds" / "phase-1" / "Spec-v1-archived.md"
    suffix_archived.write_text("# Archived spec\n", encoding="utf-8")
    prompt_doc = tmp_path / "prompts" / "agent.md"
    prompt_doc.parent.mkdir(parents=True, exist_ok=True)
    prompt_doc.write_text("See `../docs/prds/phase-1/Spec-v1-archived.md`.\n", encoding="utf-8")

    report = build_canon_lineage_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "archived_canon_reference_in_active_surface"
    assert finding.source_path == "prompts/agent.md"


def test_check_canon_lineage_cli_writes_json_report(tmp_path: Path) -> None:
    _write_canon_lineage_repo(tmp_path)
    output_path = tmp_path / "artifacts" / "drift" / "canon_lineage.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_canon_lineage.py",
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

    assert payload["scan_name"] == "canon_lineage"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0


def test_repo_canon_lineage_scan_has_no_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_canon_lineage_report(repo_root)

    assert report.findings == ()


def _write_canon_lineage_repo(root: Path) -> None:
    archive_dir = root / "docs" / "prds" / "phase-1" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.joinpath("PRD-1.1-example-v1-archived.md").write_text("# PRD Example v1\n", encoding="utf-8")

    active_dir = root / "docs" / "prds" / "phase-1"
    active_dir.mkdir(parents=True, exist_ok=True)
    active_dir.joinpath("PRD-1.1-example-v2.md").write_text(
        "\n".join(
            [
                "# PRD Example v2",
                "",
                "- **Supersedes:** `archive/PRD-1.1-example-v1-archived.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

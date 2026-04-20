from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.backlog_materialization import build_backlog_materialization_report


def test_backlog_materialization_detects_missing_decomposed_work_items(tmp_path: Path) -> None:
    _write_repo_with_ready_prd(tmp_path)

    report = build_backlog_materialization_report(tmp_path)

    assert report.stats.active_prds_scanned == 1
    assert report.stats.prds_with_issue_decomposition == 1
    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_decomposed_work_items"
    assert finding.source_path == "docs/prds/phase-2/PRD-9.1-example.md"
    assert finding.related_paths == ("WI-9.1.1", "WI-9.1.2", "WI-9.1.3")


def test_backlog_materialization_accepts_live_work_items_in_any_stage(tmp_path: Path) -> None:
    _write_repo_with_ready_prd(tmp_path)
    _write_work_item(tmp_path, "done", "WI-9.1.1")
    _write_work_item(tmp_path, "ready", "WI-9.1.2")
    _write_work_item(tmp_path, "blocked", "WI-9.1.3")

    report = build_backlog_materialization_report(tmp_path)

    assert report.findings == ()
    assert report.stats.live_work_items_indexed == 3


def test_backlog_materialization_matches_simple_numeric_work_item_ids(tmp_path: Path) -> None:
    prd_dir = tmp_path / "docs" / "prds" / "phase-2"
    prd_dir.mkdir(parents=True, exist_ok=True)
    prd_dir.joinpath("PRD-9.2-example.md").write_text(
        "\n".join(
            [
                "# PRD-9.2: Example",
                "",
                "## Header",
                "",
                "- **Status:** Ready for implementation",
                "",
                "## Issue decomposition guidance",
                "",
                "1. **WI-123 — Single numeric slice**",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_backlog_materialization_report(tmp_path)

    assert report.stats.findings_count == 1
    assert report.findings[0].related_paths == ("WI-123",)


def test_check_backlog_materialization_cli_writes_json_report(tmp_path: Path) -> None:
    _write_repo_with_ready_prd(tmp_path)
    _write_work_item(tmp_path, "done", "WI-9.1.1")
    _write_work_item(tmp_path, "ready", "WI-9.1.2")
    _write_work_item(tmp_path, "blocked", "WI-9.1.3")
    output_path = tmp_path / "artifacts" / "drift" / "backlog_materialization.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_backlog_materialization.py",
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

    assert payload["scan_name"] == "backlog_materialization"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0


def _write_repo_with_ready_prd(root: Path) -> None:
    prd_dir = root / "docs" / "prds" / "phase-2"
    prd_dir.mkdir(parents=True, exist_ok=True)
    prd_dir.joinpath("PRD-9.1-example.md").write_text(
        "\n".join(
            [
                "# PRD-9.1: Example",
                "",
                "## Header",
                "",
                "- **Status:** Ready for implementation",
                "",
                "## Issue decomposition guidance",
                "",
                "1. **WI-9.1.1 — First slice**",
                "2. **WI-9.1.2 — Second slice**",
                "3. **WI-9.1.3 — Third slice**",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_work_item(root: Path, stage: str, wi_id: str) -> None:
    work_item_path = root / "work_items" / stage / f"{wi_id}-example.md"
    work_item_path.parent.mkdir(parents=True, exist_ok=True)
    work_item_path.write_text(f"# {wi_id}\n", encoding="utf-8")
